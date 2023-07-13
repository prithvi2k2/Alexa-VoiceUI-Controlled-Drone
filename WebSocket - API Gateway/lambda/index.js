// API GateWay WebSocket Server which connects GCS to which drone is connected with and User interacting with Alexa device/app

const AWS = require('aws-sdk');

const ENDPOINT = process.env.ApiEndpoint; // AWS ApiGateway endpoint
const gatewayClient = new AWS.ApiGatewayManagementApi({endpoint: ENDPOINT});
const dbClient = new AWS.DynamoDB.DocumentClient();
const Table = process.env.TABLE; // Database Table name

// Add a new connection to DB
const addToDb = async (cid)=>{
    try{
        await dbClient.put({
            TableName: Table,
            Item: {"cid":cid},
        }).promise();
    }
    catch(err){
        console.log(err);
    }
};

// Delete a connection from DB
const delFromDb = async (cid)=>{
    try{
        await dbClient.delete({
            TableName: Table,
            Key: {
                'cid': cid
            }
        }).promise();
    }
    catch(err){
        console.log(err);
    }
};

// Retrieves all Connection IDs of currently connected clients from database
const getAllCids = async ()=>{
    try{
        let res = await dbClient.scan({
            TableName: Table,
            ProjectionExpression: "cid",
        }).promise();
        let cids = res.Items.map(obj=>obj.cid);
        return cids;
    }
    catch(err){
        console.log(err);
    }
};

// Sends message to a specified client
const respondOne = async (cid, body)=>{
    try{
        await gatewayClient.postToConnection({
            'ConnectionId': cid,
            'Data': body
        }).promise();
    }
    catch(err){
        console.log(err);
    }
};

// Sends messages to all the connected clients(except the one which triggered this function)
const respondAll = async (reqCid, body)=>{
    let cids = await getAllCids();
    try{
        const allResps = cids.map(cid => {
            if(cid!=reqCid) return respondOne(cid,body);
            });
        return Promise.all(allResps);
    }
    catch(err){
        console.log(err);
    }
};


exports.handler = async (event) => {
    
    // Classifying request routes from API gateway
    // TO handle each route in its own way
    if(event.requestContext){
        const context = event.requestContext;
        const cid = context.connectionId; // Connection ID
        const route = context.routeKey;
        
        // Handling requests based on routes
        switch(route){
            case '$connect':
                // On connecting with a client, store it's connectionId in database
                await addToDb(cid);
                break;
            case '$disconnect':
                // When a client disconnects, remove it's connectionId from database
                await delFromDb(cid);
                break;
            case 'echo':
                // Echoing message using `respondOne` function to send message to itself
                await respondOne(cid,event.body);
                break;
            case 'broadcast':
                // Passes message from one client to other connected client(s)
                await respondAll(cid,event.body);
                break;
            case '$default':
                break;
            default:
                return {
                    statusCode: 404,
                    body: `Invalid Interaction - Requested "action" not found`
                };
        }
    }
    
    const response = {
        statusCode: 200
    };
    return response;
};
