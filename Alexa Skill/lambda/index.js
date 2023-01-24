const Alexa = require('ask-sdk-core');
const AWS = require("aws-sdk");
const WebSocket = require("ws");

// DDB Client
const docClient = new AWS.DynamoDB.DocumentClient();

// Triggered when user calls the skill without INTENTS
const LaunchRequestHandler = {
  canHandle(handlerInput) {
    return handlerInput.requestEnvelope.request.type === 'LaunchRequest';
  },
  async handle(handlerInput) {
    let doc = {
        "id" : handlerInput.requestEnvelope.request.timestamp,
        "command" : "Launch Voice Pilot"
    };
    
    const resp = await wsSend({'action':'broadcast','body':{'type':'launch'}});
    let STATUS = resp.STATUS, mode = resp.mode;
    dbLog(doc);
    
    let output = `Your drone is in ${mode} mode, `;
    
    if(STATUS==1) output+='say "take off" to start drone';
    else output+=`and flying, you can say ${getRandCmd()}`;
    
    
    return handlerInput.responseBuilder
      .speak(output)
      .reprompt() // reprompt continues convo
      .getResponse();
  },
};


const TakeoffHandler = {
  canHandle(handlerInput) {
    return handlerInput.requestEnvelope.request.type === 'IntentRequest'
     && Alexa.getIntentName(handlerInput.requestEnvelope) === 'takeoff';
  },
  async handle(handlerInput){
    const resp = await wsSend({'action':'broadcast',
    'body':{
      'type': 'takeoff'
      }
    });
    let STATUS = resp.STATUS, mode = resp.mode;
    let output;
    
    if(STATUS==1) output = `launching drone`;
    else output = `drone already tookoff and is in ${mode} mode`;
    output+= `, you can now say ${getRandCmd()}`;
    return handlerInput.responseBuilder
      .speak(output)
      .reprompt()
      .getResponse(); 
  }
};


const FlyHandler = {
  canHandle(handlerInput) {
    return handlerInput.requestEnvelope.request.type === 'IntentRequest'
     && Alexa.getIntentName(handlerInput.requestEnvelope) === 'fly';
  },
  async handle(handlerInput){
    const intent = handlerInput.requestEnvelope.request.intent;
    const slots = intent.slots;
    let dir = slots['dir'].value, verb = null || slots['action'].value, dist = slots['dist'].value;
    // Get Canonical value for respective synonyms
    let canonicalDir = intent.slots.dir.resolutions.resolutionsPerAuthority[0].values[0].value.name;
    let cmd = `${verb} ${dir} ${dist || ""}`;
    
    let doc = {
        "id" : handlerInput.requestEnvelope.request.timestamp,
        "command" : cmd
    };
    dbLog(doc);
    
    const resp = await wsSend({'action':'broadcast',
    'body':{
      'type': 'fly',
      'verb': verb,
      'dir': canonicalDir,
      'dist': dist,
      }
    });
    let STATUS = resp.STATUS;
    
    let output;
    if(STATUS==1) output = `Please takeoff drone to continue, say "initiate takeoff"`;
    else if(STATUS==2) output = `${verb || "fly"}ing ${dir} ${dist?`by ${dist} meters`:''}`;
    else if(STATUS==-1) output = `command rejected - fence altitude breach`;
    else if(STATUS==-2) output = `command rejected - fence radius breach`;
    else output = `command rejected - pilot is busy`;
    
    return handlerInput.responseBuilder
      .speak(output)
      .reprompt()
      .getResponse();
  },
};


const StatusHandler = {
  canHandle(handlerInput) {
    return handlerInput.requestEnvelope.request.type === 'IntentRequest'
     && Alexa.getIntentName(handlerInput.requestEnvelope) === 'status';
  },
  async handle(handlerInput){
    const resp = await wsSend({'action':'broadcast','body':{'type':'status'}});
    let STATUS = resp.STATUS, mode = resp.mode, dist = resp.homeDist, output;
    switch (STATUS){
      case 0: output=`drone is flying to target in ${mode} mode`;
        break;
      case 1: output=`drone is at home location in ${mode} mode, say "takeoff" to start drone`;
        break;
      case 2: output=`drone reached target and is in ${mode} mode ${dist} meters away from home`;
        break;
      default:
        // when we dont get any output/no gcs is online
        output = 'no pilot is online';
    }
    
    return handlerInput.responseBuilder
      .speak(output)
      .reprompt()
      .getResponse();
    },
};


const RtlHandler = {
  canHandle(handlerInput){
    return handlerInput.requestEnvelope.request.type === 'IntentRequest'
     && Alexa.getIntentName(handlerInput.requestEnvelope) === 'rtl';
  },
  async handle(handlerInput){
    let doc = {
        "id" : handlerInput.requestEnvelope.request.timestamp,
        "command" : "RTL command"
    };
    
    const resp = await wsSend({'action':'broadcast','body':{'type':'rtl'}});
    dbLog(doc);
    
    let STATUS = resp.STATUS , output;
    
    if(STATUS==2) output = "returning to launch";
    else if(STATUS==1) output = "your drone didn't takeoff, already at home, you can say 'takeoff'";
    else output = "Pilot flying to another target, try after reaching target";
    
    return handlerInput.responseBuilder
      .speak(output)
      .reprompt()
      .getResponse();
    },
};

const HelpHandler = {
  canHandle(handlerInput) {
    return handlerInput.requestEnvelope.request.type === 'IntentRequest'
      && handlerInput.requestEnvelope.request.intent.name === 'AMAZON.HelpIntent';
  },
  handle(handlerInput) {
    const speakOutput = `Use words like 'fly', 'move' along with direction and distance in meters to control the Drone.
                        For example : "Fly Higher by 5 meters", "Move west 10", "go north 15", "Fly Lower"`;

    return handlerInput.responseBuilder
      .speak(speakOutput)
      .getResponse();
  },
};

const CancelAndStopHandler = {
  canHandle(handlerInput) {
    return handlerInput.requestEnvelope.request.type === 'IntentRequest'
      && (handlerInput.requestEnvelope.request.intent.name === 'AMAZON.CancelIntent'
        || handlerInput.requestEnvelope.request.intent.name === 'AMAZON.StopIntent');
  },
  handle(handlerInput) {
    const speakOutput = 'Hope you had a safe flight pilot, See you again!';

    return handlerInput.responseBuilder
      .speak(speakOutput)
      .getResponse();
  },
};

const SessionEndedRequestHandler = {
  canHandle(handlerInput) {
    return handlerInput.requestEnvelope.request.type === 'SessionEndedRequest';
  },
  handle(handlerInput) {
    console.log(`Session ended with reason: ${handlerInput.requestEnvelope.request.reason}`);

    return handlerInput.responseBuilder.getResponse();
  },
};

const ErrorHandler = {
  canHandle() {
    return true;
  },
  handle(handlerInput, error) {
    console.log(`Error handled: ${error.message}`);
    console.log(error.trace);

    return handlerInput.responseBuilder
      .speak('Sorry, I can\'t understand the command. Please say again.')
      .reprompt()
      .getResponse();
  },
};

// UTIL

// source : aws amplify docs for using dynamoDB
const dbLog = async (doc)=>{
  const params = {
    TableName : process.env.TABLE,
    Item: doc,
    };
    // Insert to DB
    try {
      await docClient.put(params).promise();
      } catch (err) {
        console.log(err);
      }
};

const wsSend = doc=>{
  return new Promise((resolve,reject)=>{
    const ws = new WebSocket('wss://32226u87yi.execute-api.eu-west-1.amazonaws.com/test_experiment');
    ws.onmessage = function (msg) {
      let body = msg.data;
      console.log('wsreceived: %s', body);
      ws.close();
     resolve(JSON.parse(body));
     reject("ws error");
    };
    ws.onopen = () => {
      ws.send(JSON.stringify(doc));
    };
  });
};


let cmds = [
  "move north by 5 meters",
  "move south by 5 meters",
  "move east by 5 meters",
  "move west by 5 meters",
  "return to home",
  "fly lower by 3 meters",
  "fly higher by 3 meters"
  ];

function getRandCmd(isVerticalPlane=1){
  let min = 0, max = cmds.length;
  if(isVerticalPlane==0) min=4;
  // return a cmd[x] where x is random value in [min,max)
  return cmds[Math.floor(Math.random() * (max - min) + min)];
}


const skillBuilder = Alexa.SkillBuilders.custom();

exports.handler = skillBuilder
  .addRequestHandlers(
    LaunchRequestHandler,
    TakeoffHandler,
    FlyHandler,
    StatusHandler,
    RtlHandler,
    HelpHandler,
    CancelAndStopHandler,
    SessionEndedRequestHandler,
  )
  .addErrorHandlers(ErrorHandler)
  .withApiClient(new Alexa.DefaultApiClient())
  .lambda();