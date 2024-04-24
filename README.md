
# AWS CDK Project to deploy the solution to transcribe and summarize call center calls between agents and customers

This repository represents the AWS CDK project, which, once deployed, provides a basic solution to transcribe the call between the call center agent and the customer.

The process starts by uploading the audio file to the S3 bucket. The lambda function will pick up the file and call Amazon Transcribe to convert speech to text. Another Lambda will capture transcription job completion status and will do the following:

1. Call Amazon Bedrock Large Language Model to get insights from the text. We capture the summary of the call, the tone of the call and the sentiment. The data provided in JSON format.

2. JSON data is stored into Dynamo DB table

3. JSON data is also being send by email. Email also contains the chain of thought that LLM took.

# Prerequisites

You need to install AWS CDK following this instructions https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html.

# Deployment
```
cdk deploy CallCenterPyStack -f  --parameters snstopicemailparam=YOUR_EMAIL@dummy.com
```
Note the "snstopicemailparam" parameter. This is the email address that you will get the JSON that is described above.
 
Also note that before actually getting the JSON by email, you will get another email that asks you to verify your email.

# Architecture
<img width="819" alt="image" src="https://github.com/MichaelShapira/CallCenterPy/assets/135519473/e64e1651-dd57-49dd-a073-94e235166328">


# Customization

The summarization Lambda allows you to choose which model to use to get insights. By default, Claude Haiku is used.
You can also specify the language that will be used to describe the chain of thought that the model followed.

 <img width="797" alt="image" src="https://github.com/MichaelShapira/CallCenterPy/assets/135519473/59c8b8ef-20a9-4c0c-bc1c-628aa09e517e">

 The transcription Lambda allows you to specify the language of the audio file you want to analyze. The default language is "he-IL" (Hebrew)
 <img width="839" alt="image" src="https://github.com/MichaelShapira/CallCenterPy/assets/135519473/b131436c-1266-47c5-b070-76f03d018407">


# Identify Objects
At the end of the deployment process you can view the objects name in output section
<img width="1178" alt="image" src="https://github.com/MichaelShapira/CallCenterPy/assets/135519473/5988cf94-2bcf-49a5-ba2d-123c4b64bc1c">

# Getting Started
Simply upload the audio file to the S3 bucket that appears in "CallCenterPyStack.UploadAudioFileToThisS3bucket" output value

