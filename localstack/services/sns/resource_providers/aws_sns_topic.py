# LocalStack Resource Provider Scaffolding v2
from __future__ import annotations

from pathlib import Path
from typing import Optional, Type, TypedDict

import localstack.services.cloudformation.provider_utils as util
from localstack.services.cloudformation.resource_provider import (
    CloudFormationResourceProviderPlugin,
    OperationStatus,
    ProgressEvent,
    ResourceProvider,
    ResourceRequest,
)
from localstack.utils.strings import short_uid


class SNSTopicProperties(TypedDict):
    ContentBasedDeduplication: Optional[bool]
    DataProtectionPolicy: Optional[dict]
    DisplayName: Optional[str]
    FifoTopic: Optional[bool]
    KmsMasterKeyId: Optional[str]
    SignatureVersion: Optional[str]
    Subscription: Optional[list[Subscription]]
    Tags: Optional[list[Tag]]
    TopicArn: Optional[str]
    TopicName: Optional[str]
    TracingConfig: Optional[str]


class Subscription(TypedDict):
    Endpoint: Optional[str]
    Protocol: Optional[str]


class Tag(TypedDict):
    Key: Optional[str]
    Value: Optional[str]


REPEATED_INVOCATION = "repeated_invocation"


class SNSTopicProvider(ResourceProvider[SNSTopicProperties]):
    TYPE = "AWS::SNS::Topic"  # Autogenerated. Don't change
    SCHEMA = util.get_schema_path(Path(__file__))  # Autogenerated. Don't change

    def create(
        self,
        request: ResourceRequest[SNSTopicProperties],
    ) -> ProgressEvent[SNSTopicProperties]:
        """
        Create a new resource.

        Primary identifier fields:
          - /properties/TopicArn



        Create-only properties:
          - /properties/TopicName
          - /properties/FifoTopic

        Read-only properties:
          - /properties/TopicArn

        IAM permissions required:
          - sns:CreateTopic
          - sns:TagResource
          - sns:Subscribe
          - sns:GetTopicAttributes
          - sns:PutDataProtectionPolicy

        """
        model = request.desired_state
        sns = request.aws_client_factory.sns
        # TODO: validations and iam checks

        attributes = {k: v for k, v in model.items() if v is not None if k != "TopicName"}

        # following attributes need to be str instead of bool for boto to work
        if attributes.get("FifoTopic") is not None:
            attributes["FifoTopic"] = str(attributes.get("FifoTopic"))

        if attributes.get("ContentBasedDeduplication") is not None:
            attributes["ContentBasedDeduplication"] = str(
                attributes.get("ContentBasedDeduplication")
            )

        subscriptions = []
        if attributes.get("Subscription") is not None:
            subscriptions = attributes["Subscription"]
            del attributes["Subscription"]

        tags = []
        if attributes.get("Tags") is not None:
            tags = attributes["Tags"]
            del attributes["Tags"]

        # in case cloudformation didn't provide topic name
        if model.get("TopicName") is None:
            model["TopicName"] = f"topic-{short_uid()}"

        create_sns_response = sns.create_topic(Name=model["TopicName"], Attributes=attributes)
        request.custom_context[REPEATED_INVOCATION] = True
        model["TopicArn"] = create_sns_response["TopicArn"]

        # now we add subscriptions if they exists
        for subscription in subscriptions:
            sns.subscribe(
                TopicArn=model["TopicArn"],
                Protocol=subscription["Protocol"],
                Endpoint=subscription["Endpoint"],
            )
        if tags:
            sns.tag_resource(ResourceArn=model["TopicArn"], Tags=tags)

        return ProgressEvent(
            status=OperationStatus.SUCCESS,
            resource_model=model,
            custom_context=request.custom_context,
        )

    def read(
        self,
        request: ResourceRequest[SNSTopicProperties],
    ) -> ProgressEvent[SNSTopicProperties]:
        """
        Fetch resource information

        IAM permissions required:
          - sns:GetTopicAttributes
          - sns:ListTagsForResource
          - sns:ListSubscriptionsByTopic
          - sns:GetDataProtectionPolicy
        """
        raise NotImplementedError

    def delete(
        self,
        request: ResourceRequest[SNSTopicProperties],
    ) -> ProgressEvent[SNSTopicProperties]:
        """
        Delete a resource

        IAM permissions required:
          - sns:DeleteTopic
        """
        model = request.desired_state
        sns = request.aws_client_factory.sns
        sns.delete_topic(TopicArn=model["TopicArn"])
        return ProgressEvent(status=OperationStatus.SUCCESS, resource_model={})

    def update(
        self,
        request: ResourceRequest[SNSTopicProperties],
    ) -> ProgressEvent[SNSTopicProperties]:
        """
        Update a resource

        IAM permissions required:
          - sns:SetTopicAttributes
          - sns:TagResource
          - sns:UntagResource
          - sns:Subscribe
          - sns:Unsubscribe
          - sns:GetTopicAttributes
          - sns:ListTagsForResource
          - sns:ListSubscriptionsByTopic
          - sns:GetDataProtectionPolicy
          - sns:PutDataProtectionPolicy
        """
        raise NotImplementedError


class SNSTopicProviderPlugin(CloudFormationResourceProviderPlugin):
    name = "AWS::SNS::Topic"

    def __init__(self):
        self.factory: Optional[Type[ResourceProvider]] = None

    def load(self):
        self.factory = SNSTopicProvider
