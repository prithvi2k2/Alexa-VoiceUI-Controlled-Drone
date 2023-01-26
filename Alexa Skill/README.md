##### [🔙Back to Home](https://github.com/prithvi2k2/Alexa-VoiceUI-Controlled-Drone/#alexa-voiceui-controlled-drone)
---

Skills are like apps for Alexa. With an interactive voice interface, Alexa gives users a hands-free way to interact with your skill. Here, __we build a custom Alexa skill for interaction/communication between the end-user and the ground control station__

Steps to reproduce the custom Alexa skill:

- Create a custom skill from scratch in the Alexa console using an amazon developer account
- Upload the schema definition [json](./InteractionModel.json) file in your new skill's `Interaction Model > JSON Editor` and save
- On successfully cloning schema to your skill, all that has to be done is set up a lambda function
- Use the provided lambda [directory](./lambda/) which is written in `Node.js 16.x` to install `npm modules` in your local environment
- After installing modules, compress all files in the directory into a `.zip` file and upload them to your AWS Lambda function
- Create a DynamoDB table `YOUR_TABLE` for logging commands given by end-users
- Now add the table name as a Lambda function's environment variable `TABLE: YOUR_TABLE`
- Integrate the lambda function and Alexa skill, using the lambda function's ARN and Alexa skill ID
- Finally, deploy the lambda function

## Known issues

- WebSocket connections are not persisted by stateless lambda sometimes