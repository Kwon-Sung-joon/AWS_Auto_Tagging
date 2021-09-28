import json
import boto3
import logging
from botocore.exceptions import ClientError
import botocore
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_ssm_parameter_tags(event):
    
    try:
        eventSource = event['detail']['eventSource'].split(".")
        eventSource = eventSource[0]
        
    except Exception as e:
        eventSource = []

    tag_list = list()
    
    try:
        path_string = "/auto-tag/tag"
        ssm_client = boto3.client('ssm', 'ap-northeast-2')
        get_parameter_response = ssm_client.get_parameters_by_path(
        Path=path_string,
        Recursive=True,
        WithDecryption=True
        )
        
        for parameter in get_parameter_response['Parameters']:
            tag_dictionary = dict()
            path_components = parameter['Name'].split("/")
            tag_key = path_components[-1]
            if tag_key == 'Name':
                tag_dictionary['Key'] = tag_key
                tag_dictionary['Value'] = parameter['Value'] + eventSource.upper()
                tag_list.append(tag_dictionary)
            else:
                tag_dictionary['Key'] = tag_key
                tag_dictionary['Value'] = parameter['Value']
                tag_list.append(tag_dictionary)
        return tag_list
        
    except botocore.exceptions.ClientError as error:
        print("Boto3 API returned error: ", error)
        tag_list.clear()
        
        
    return tag_list

def aws_create_tag(_aws_region, _target: str, tag_list):

    try:
        client = boto3.client('ec2', region_name=_aws_region)
        client.create_tags(Resources=[_target, ], Tags=tag_list)
        logging.info(f'successfuly created tag {tag_list} for instance {_target}')
        
    except ClientError:
        
        logging.info(str(ClientError))
        return False
    return True
    
    
    


def getUser_name(event):
    #Check user_name
    if 'detail' in event:
        try:
            if 'userIdentity' in event['detail']:
                if event['detail']['userIdentity']['type'] == 'AssumedRole':
                    user_name = str('UserName: ' + event['detail']['userIdentity']['principalId'].split(':')[1] + ', Role: ' + event['detail']['userIdentity']['sessionContext']['sessionIssuer']['userName'] + ' (role)')
                elif event['detail']['userIdentity']['type'] == 'IAMUser':
                    user_name = event['detail']['userIdentity']['userName']
                elif event['detail']['userIdentity']['type'] == 'Root':
                    user_name = 'root'
                    
                else:
                    logging.info('Could not determine username (unknown iam userIdentity) ')
                    user_name = ''
            else:
                logging.info('Could not determine username (no userIdentity data in cloudtrail')
                user_name = ''
        except Exception as e:
            logging.info('could not find username, exception: ' + str(e))
            user_name = ''

    return user_name




def addInsatncesTag(event,user_name,tag_list):
            
        try:
            instance_id = [x['instanceId'] for x in event['detail']['responseElements']['instancesSet']['items']]
        except Exception as e:
        
         instance_id = []
        aws_region = event['detail']['awsRegion']
        client = boto3.client('ec2', region_name=aws_region)
        
        if instance_id:
            for instance in instance_id:
                # Let's tag the instance
                instance_api = client.describe_instances(InstanceIds=[instance])

                
                # Get all ec2 instance tags
                if 'Tags' in instance_api['Reservations'][0]['Instances'][0]:
                    instance_tags = instance_api['Reservations'][0]['Instances'][0]['Tags']
                else:
                    instance_tags = []
                    
                    
                # Check if 'Name' tag is exist for ec2 instance
                if instance_tags:
                    instance_name = [x['Value'] for x in instance_tags if x['Key'] and x['Key'] == 'Name']
                    if instance_name:
                        instance_name = instance_name[0]
                else:
                    instance_name = ''
                    
                    
                    
                # Check if 'Owner' tag exist in instance tags
                if instance_tags:
                    if not any(keys.get('Key') == 'Owner' for keys in instance_tags):
                        logging.info(f'Tag "Owner" doesn\'t exist for instance {instance}, creating...')
                        
                        idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                        tag_list[idx]['Value'] += ('-'+ instance)
                        aws_create_tag(aws_region, instance, tag_list)
                    else:
                        logging.info(f'Owner tag already exist for instance {instance}')
                else:
                    
                    logging.info(f'Instance {instance} has no tags, let\'s tag it with Owner tag')
                    idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                    tag_list[idx]['Value'] += ('-'+ instance)
                    aws_create_tag(aws_region, instance, tag_list)
        
                # Let's tag the instance volumes
                
                
                AttachedInstance = dict()
                AttachedInstance['Key'] = 'AttachedInstance'
                AttachedInstance['Value'] = instance
                tag_list.append(AttachedInstance)  
            
                instance_volumes = [x['Ebs']['VolumeId'] for x in instance_api['Reservations'][0]['Instances'][0]['BlockDeviceMappings']]
                # Check if volume already has tags
                for volume in instance_volumes:
                    response = client.describe_volumes(VolumeIds=[volume])
                    volume_tags = [x['Tags'] for x in response['Volumes'] if 'Tags' in x]
                    if volume_tags:
                        if any(keys.get('Key') == 'Owner' and keys.get('Key') == 'AttachedInstance' for keys in
                                   volume_tags[0]):
                            logging.info(
                                f'Nothing to tag for volume {volume} of instance: {instance}, is already tagged')
                            continue
                        if not any(keys.get('Key') == 'Owner' for keys in volume_tags[0]):
                            logging.info('Tag "Owner" doesn\'t exist, creating...')
                            idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                            tag_list[idx]['Value'] += ('-'+ volume)
                            aws_create_tag(aws_region, volume, tag_list)
                        if not any(keys.get('Key') == 'AttachedInstance' for keys in volume_tags[0]):
                            logging.info('Tag "AttachedInstance" doesn\'t exist, creating...')
                            idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                            tag_list[idx]['Value'] += ('-'+ volume)
                            aws_create_tag(aws_region, volume, tag_list)
                    else:
                        logging.info(f'volume {volume} is not tagged, adding Owner and AttachedInstance tags')
                        #aws_create_tag(aws_region, volume, 'AttachedInstance', instance + ' - ' + str(instance_name))
                        
                        idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                        tag_list[idx]['Value'] += ('-'+ volume)
                        aws_create_tag(aws_region, volume, tag_list)
                        
                        
                        
                        
            return {
                'user_name' : user_name,
                'statusCode': 200,
                'body': json.dumps('All Done!')
            }
        else:
            return {
                'statusCode': 200,
                'body': json.dumps('No Data!')
            }


    
def addVpcTag(event,user_name,tag_list):
        try:
            vpc_id = event['detail']['responseElements']['vpc']['vpcId']
        except Exception as e:
            vpc_id = []

        aws_region = event['detail']['awsRegion']
        client = boto3.client('ec2', region_name=aws_region)
        
        if vpc_id:
            vpc_api = client.describe_vpcs(VpcIds=[vpc_id])

            if 'Tags' in vpc_api['Vpcs'][0]:
                    vpc_tags = vpc_api['Vpcs'][0]['Tags']
            else:
                    vpc_tags = []
            if vpc_tags:
                if not any(keys.get('Key') == 'Owner' for keys in vpc_tags):
                    logging.info(f'Tag "Owner" doesn\'t exist for vpc {vpc_id}, creating...')
                    idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                    tag_list[idx]['Value'] += ('-'+ vpc_id)
                    aws_create_tag(aws_region, vpc_id, tag_list)
                else:
                    logging.info(f'Owner tag already exist for vpc {vpc_id}')
            else:
                logging.info(f'Vpc {vpc_id} has no tags, let\'s tag it with Owner tag')
                idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                tag_list[idx]['Value'] += ('-'+ vpc_id)
                aws_create_tag(aws_region, vpc_id, tag_list)
        
            return {
                'user_name' : user_name,
                'statusCode': 200,
                'body': json.dumps('All Done!')
            }
        else:
            return {
                'user_name' : user_name,
                'statusCode': 200,
                'body': json.dumps('No Data!')
            }
        
def addSubnetTag(event,user_name,tag_list):
        
        
        
        try:
            subnet_id = event['detail']['responseElements']['subnet']['subnetId']
        except Exception as e:
            subnet_id = []
        
        aws_region = event['detail']['awsRegion']
        
        if subnet_id:
            client = boto3.resource('ec2', region_name=aws_region).Subnet(subnet_id)


            if client.tags:
                    subnet_tags = client.tags
            else:
                    subnet_tags = []
            if subnet_tags:
                if not any(keys.get('Key') == 'Owner' for keys in subnet_tags):
                    logging.info(f'Tag "Owner" doesn\'t exist for subnet {subnet_id}, creating...')
                    idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                    tag_list[idx]['Value'] += ('-'+ subnet_id)
                    aws_create_tag(aws_region, subnet_id, tag_list)
                else:
                    logging.info(f'Owner tag already exist for subnet {subnet_id}')
            else:
                logging.info(f'Subnet {subnet_id} has no tags, let\'s tag it with Owner tag')
                idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                tag_list[idx]['Value'] += ('-'+ subnet_id)
                aws_create_tag(aws_region, subnet_id, tag_list)
        
            return {
                'user_name' : user_name,
                'statusCode': 200,
                'body': json.dumps('All Done!')
            }
        else:
            return {
                'user_name' : user_name,
                'statusCode': 200,
                'body': json.dumps('No Data!')
            }
        
def addS3Tag(event,user_name,tag_list):

        try:
            bucket_name = event['detail']['requestParameters']['bucketName']
            

        except Exception as e:
            bucket_name = []
            
        if bucket_name:
            aws_region = event['region']
            client = boto3.client('s3');
            try:
                s3_api = client.get_bucket_tagging(Bucket=bucket_name);
            except Exception as e:
                s3_api = []
            
            
            if 'TagSet' in s3_api:
                    bucket_tags = s3_api['TagSet']
            else: 
                    logging.info(f'S3 {bucket_name} doesn\'t have any tags...')

                    bucket_tags = [{'Key': '', 'Value': ''}]
                    
                    

            if bucket_tags:
                if not any(keys.get('Key') == 'Owner' for keys in bucket_tags):
                    logging.info(f'Tag "Owner" doesn\'t exist for S3 {bucket_name}, creating...')
                    idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                    tag_list[idx]['Value'] += ('-'+ bucket_name)
                    response = client.put_bucket_tagging(
                        Bucket=bucket_name,
                        Tagging={
                          'TagSet' : tag_list
                        })
            
                else:
                    logging.info(f'Owner tag already exist for s3 {bucket_name}')
            else:
                logging.info(f'S3 {bucket_name} has no tags, let\'s tag it with Owner tag')
            
                idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                tag_list[idx]['Value'] += ('-'+ bucket_name)
                response = client.put_bucket_tagging(
                        Bucket=bucket_name,
                        Tagging={
                          tag_list  
                        })
        
            return {
                'user_name' : user_name,
                'statusCode': 200,
                'body': json.dumps('All Done!')
            }
        else:
            return {
                'user_name' : user_name,
                'statusCode': 200,
                'body': json.dumps('No Data!')
            }

                   

def addSecurityGroupTag(event,user_name,tag_list):
    
        try:
            sg_id = event['detail']['responseElements']['groupId']
        except Exception as e:
            sg_id = []

        aws_region = event['detail']['awsRegion']
        client = boto3.client('ec2', region_name=aws_region)
        
        if sg_id:
            sg_api = client.describe_security_groups(GroupIds=[sg_id])

            if 'Tags' in sg_api['SecurityGroups'][0]:
                    sg_tags = sg_api['SecurityGroups'][0]['Tags']
            else:
                    sg_tags = []
            if sg_tags:
                if not any(keys.get('Key') == 'Owner' for keys in sg_tags):
                    logging.info(f'Tag "Owner" doesn\'t exist for SG {sg_id}, creating...')
                    
                    idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                    tag_list[idx]['Value'] += ('-'+ sg_id)
                    
                    aws_create_tag(aws_region, sg_id, tag_list)
                else:
                    
                    idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                    tag_list[idx]['Value'] += ('-'+ sg_id)
                    
                    logging.info(f'Owner tag already exist for SG {sg_id}')
            else:
                logging.info(f'SG {sg_id} has no tags, let\'s tag it with Owner tag')
                
                idx = next(( i for (i,item) in enumerate(tag_list) if item['Key'] == 'Name'),None);
                tag_list[idx]['Value'] += ('-'+ sg_id)
                    
                aws_create_tag(aws_region, sg_id, tag_list)
        
            return {
                'user_name' : user_name,
                'statusCode': 200,
                'body': json.dumps('All Done!')
            }
        else:
            return {
                'user_name' : user_name,
                'statusCode': 200,
                'body': json.dumps('No Data!')
            }


    
def lambda_handler(event, context):

    user_name=getUser_name(event);

    tag_list= list()
    
    #get SSM Parameter Stores
    tag_list=get_ssm_parameter_tags(event) 
    
    
    created_by = dict()
    
    #Add user_name tag
    created_by['Key'] = 'CreateBy'
    created_by['Value'] = user_name
    tag_list.append(created_by)  

    print(tag_list)
    
    
    if event['detail']['eventName'] == 'RunInstances':
        addInsatncesTag(event,user_name,tag_list);
    
    if event['detail']['eventName'] == 'CreateVpc':
        addVpcTag(event,user_name,tag_list);
    
    if event['detail']['eventName'] == 'CreateBucket':
        addS3Tag(event,user_name,tag_list);
  
    if event['detail']['eventName'] == 'CreateSecurityGroup':
        addSecurityGroupTag(event,user_name,tag_list);
      
    if event['detail']['eventName'] == 'CreateSubnet':
        addSubnetTag(event,user_name,tag_list);
        
        
        
