import json
import boto3
from urllib.parse import urlparse
import json
import os

transcribe_client = boto3.client("transcribe")
s3_client = boto3.client('s3')
bedrock_runtime = boto3.client("bedrock-runtime")
dynamodb_client = boto3.resource('dynamodb')
dynamo_table = dynamodb_client.Table(os.environ.get('DYNAMO_DB_TABLE'))
sns_client = boto3.client('sns')

transcribeText=""

def lambda_handler(event, context):
    # TODO implement
    
    job_name = event['detail']['TranscriptionJobName']
    job = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
    s3_key = job['TranscriptionJob']['Media']['MediaFileUri']
    
    mediaFile= job['TranscriptionJob']['Transcript']['TranscriptFileUri']

    o = urlparse(mediaFile, allow_fragments=False)
    s3WorkString =  o.path
    s3WorkString = s3WorkString[1:]
    
    s3WorkList = s3WorkString.split('/', 1)
    bucket = s3WorkList[0]
    bucketKey = s3WorkList[1]

    
    s3response = s3_client.select_object_content(
    Bucket=bucket,
    Key=bucketKey,
    Expression="SELECT s.* FROM S3Object s", 
    ExpressionType='SQL',
    InputSerialization={
        'JSON': {
            'Type': 'DOCUMENT'
        }
    },
    OutputSerialization={
        'JSON': {
            'RecordDelimiter': ','
        }
    }
)
    
    for event in s3response['Payload']:
        if 'Records' in event:
          records = event['Records']['Payload'].decode('utf-8')
          records=records[:-1]
         
          records = json.loads(records)
          transcribeText=records['results']['transcripts'][0]['transcript']
          
    # Model configuration
    model_id = os.environ.get('MODEL_ID')
    model_kwargs =  { 
        "max_tokens": 2048, "temperature": 0.1,
        "top_k": 250, "top_p": 1, "stop_sequences": ["\n\nHuman"],
    }
    
    steps_language = os.environ.get('STEPS_LANGUAGE')
    
    system_prompt="""
        You are an AI assistant tasked with analyzing conversations between customer and call center agent. Your responsibilities are as follows:
    
        Task 1: Analyze the provided conversation and identify the primary tone and sentiment expressed by the customer. Classify the tone as one of the following: Positive, Negative, Neutral, Humorous, Sarcastic, Enthusiastic, Angry, or Informative. Classify the sentiment as Positive, Negative, or Neutral. Provide a direct short answer without explanations.
        
        Task 2: Review the conversation and create a concise summary in Hebrew, focusing on the key topic discussed. Use clear and professional language, and describe the topic in one sentence, as if you are the customer service representative. Use a maximum of 20 words.
        
        Task 3: Determine if the call was resolved or not. A resolved call is one where nothing is left open, and the customer provided indications that the issue was resolved to their satisfaction. Classify the call outcome as Resolved, Not Resolved, or Unknown. Provide a direct short answer without explanations.
        
        Do it step by step and describe your steps in "steps" JSON element by using {steps_language} language.
        
        Your output should be in the following JSON format:
        {
          "call_sentiment": "<sentiment>",
          "call_tone": "<tone>", 
          "summary": "<summary>",
          "call_outcome": "<call_outcome>",
          "steps": "<steps>"
        }"""
    
    
    # Input configuration
    
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": transcribeText}]},
        ],
    }
    body.update(model_kwargs)
    
    # Invoke
    response = bedrock_runtime.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
    )
    
    # Process LLM response and convert to JSON
    llm_result = json.loads(response.get("body").read()).get("content", [])[0].get("text", "")
       
    dynamo_item = json.loads(llm_result)
    dynamo_item["transcribe_file"] = mediaFile
    #primary key for Dynamo table
    dynamo_item["s3_key"] =s3_key
    
    response = dynamo_table.put_item(
        Item=dynamo_item
    )
    
    sns_client.publish(TopicArn=os.environ.get('SNS_TOPIC_ARN'),Message=json.dumps(dynamo_item,ensure_ascii=False))
    print("Message published")
    
    print(response)   
    
    return {
        'statusCode': 200,
        'body': json.dumps('Audio files were converted to text and analyzed with the Amazon Bedrock Large Language Model. The results are stored in the Dynamo table and sent by email.')
    }
