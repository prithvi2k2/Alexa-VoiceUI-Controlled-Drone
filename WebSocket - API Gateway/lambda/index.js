const AWS = require('aws-sdk');

const ENDPOINT = '32226u87yi.execute-api.eu-west-1.amazonaws.com/test_experiment/';
const gatewayClient = new AWS.ApiGatewayManagementApi({endpoint: ENDPOINT});
const dbClient = new AWS.DynamoDB.DocumentClient();

const Table = process.env.TABLE;

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
                await addToDb(cid);
                break;
            case '$disconnect':
                await delFromDb(cid);
                break;
            case 'echo':
                await respondOne(cid,event.body);
                break;
            case 'broadcast':
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
