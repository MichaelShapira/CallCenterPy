from aws_cdk import (
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_iam as iam,
    RemovalPolicy,
    CfnOutput,
    CfnParameter,
    aws_dynamodb as dynamo,
    aws_s3_notifications,
    aws_sns_subscriptions as subscriptions,
    aws_sns as sns,
    aws_events as events,
    aws_events_targets as targets,
    Stack,
    # aws_sqs as sqs,
)
from constructs import Construct
import uuid
import aws_cdk as cdk

class CallCenterPyStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #role for the lambda that calls Amazon Transcribe by using the audio
        #file that was uploaded to the S3 bucket
        transcribeLambdaRole = iam.Role(self, "TranscribeLambdaRole",
                     assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
                                    )

        functionAudionToText = _lambda.Function(self, "lambda_function",
                                    runtime=_lambda.Runtime.PYTHON_3_11,
                                    handler="lambda-transcribe.lambda_handler",
                                    code=_lambda.Code.from_asset("./lambda/transcribe"),
                                    timeout=cdk.Duration.seconds(30),
                                    memory_size=256,
                                    environment={ # ADD THIS, FILL IT FOR ACTUAL VALUE 
                                                "AUDIO_LANGUAGE": "he-IL"
                                            },
                                    role = transcribeLambdaRole
                                    )

        sourceBucket = s3.Bucket(self, "CallCenterAudioFilesSource", 
                                 versioned=False,
                                 removal_policy=RemovalPolicy.DESTROY,
                                 auto_delete_objects=True)
        
        
        
        transcribeLambdaRole.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))
 

        transcribeLambdaRole.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=["transcribe:StartTranscriptionJob"]
                
            ))

        transcribeLambdaRole.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[sourceBucket.bucket_arn+"/*"],
                actions=["s3:PutObject","s3:GetObject"]
                
            ))   

        # create s3 notification for lambda function
        notification = aws_s3_notifications.LambdaDestination(functionAudionToText)

        # assign notification for the s3 event type (ex: OBJECT_CREATED)
        sourceBucket.add_event_notification(s3.EventType.OBJECT_CREATED, notification)    

        table = dynamo.TableV2(self, "Table",
              partition_key=dynamo.Attribute(name="s3_key", type=dynamo.AttributeType.STRING)
        )
        summarizeLambdaRole = iam.Role(self, "SummarizeLambdaRole",
                     assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"))
        summarizeLambdaRole.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))
        
        summarizeLambdaRole.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=["bedrock:InvokeModel"]
                
            )) 

        summarizeLambdaRole.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["dynamodb:PutItem"],
                resources=[table.table_arn]
                
            ))

        summarizeLambdaRole.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["transcribe:GetTranscriptionJob"],
                resources=["*"]
                
            )) 

        summarizeLambdaRole.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sns:Publish"],
                resources=["*"]
                
            ))

        summarizeLambdaRole.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject"],
                resources=["*"]
                
            )) 


        sns_topic = sns.Topic(self, "CallCenterTopic")

        functionSummarizeText = _lambda.Function(self, "lambda_function_summarize",
                                    runtime=_lambda.Runtime.PYTHON_3_11,
                                    handler="lambda-summarize.lambda_handler",
                                    code=_lambda.Code.from_asset("./lambda/summarize"),
                                    timeout=cdk.Duration.seconds(60),
                                    memory_size=512,
                                    role = summarizeLambdaRole,
                                    environment={ # ADD THIS, FILL IT FOR ACTUAL VALUE 
                                                "MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
                                                "SNS_TOPIC_ARN": sns_topic.topic_arn,
                                                "STEPS_LANGUAGE": "Hebrew"
                                            },
                                    )              

        
        email_address = CfnParameter(self, "sns-topic-email-param")

        sns_topic.add_subscription(subscriptions.EmailSubscription(email_address.value_as_string))

        transcribe_event = events.Rule(self, 'transcribeEventForSummarizatoinLambda',
                                           description='Completed Transcription Jobs',
                                           event_pattern=events.EventPattern(source=["aws.transcribe"],
                                                                             detail={
                                                                                 "TranscriptionJobStatus": ["COMPLETED"]
                                                                             }  
                                                                             ))

        transcribe_event.add_target(targets.LambdaFunction(handler=functionSummarizeText))                                                                             

        CfnOutput(self, "Upload Audio File To This S3 bucket", value=sourceBucket.bucket_name)
        CfnOutput(self, "The Dynamo DB Table", value=table.table_name)
        CfnOutput(self, "The EventBridge Rule", value=transcribe_event.rule_name)
        CfnOutput(self, "Transcription Job Lambda", value=functionAudionToText.function_name)
        CfnOutput(self, "Summarization Lambda", value=functionSummarizeText.function_name)