# AWS_Auto_Tagging
AWS_Auto_Tagging
![image](https://user-images.githubusercontent.com/43159901/132829934-b814d368-d7c6-45fa-8598-80ec2e91682f.png)



	1. CloudTrail 추적 생성
![image](https://user-images.githubusercontent.com/43159901/133211510-60aadf7e-a87d-43dc-b933-721dfd7b0883.png)



	2. AWS Systems Manager Parameter Store 생성
	- 파라미터의 이름: /auto-tag/tag/<Tag Key>
	- 파라미터의 값 :  <Tag Value>




	3. Lambda에 부여 할 IAM 역할 생성 (아래 정책 부여)
#### Lambda 정책 ###
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeVpcs",
                "ec2:DescribeVolumes",
                "ec2:DescribeSecurityGroups"
            ],
            "Resource": "*"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "iam:ListRoleTags",
                "ssm:GetParametersByPath"
            ],
            "Resource": [
                "arn:aws:ssm:*:<AWS ACCOUNT>:parameter/*",
                "arn:aws:iam::<AWS ACCOUNT>:role/*",
                "arn:aws:kms:*:<AWS ACCOUNT>:key/*"
            ]
        },
        {
            "Sid": "VisualEditor2",
            "Effect": "Allow",
            "Action": [
                "s3:GetBucketTagging",
                "s3:PutBucketTagging",
                "ec2:CreateTags"
            ],
            "Resource": [
                "arn:aws:s3:::*",
                "arn:aws:ec2:*:*:instance/*",
                "arn:aws:ec2:*:*:volume/*",
                "arn:aws:ec2:*:*:security-group/*",
                "arn:aws:ec2:*:*:vpc/*"
            ]
        }
    ]
}



![image](https://user-images.githubusercontent.com/43159901/133211567-0801640b-3b05-44b2-bc57-3900d7ccd750.png)
	
	

	4. Lambda 생성
	- Python 3.8 사용
	- 앞서 생성한 역할 연결


	- 함수 생성 후 '일반 구성'에서 함수 제한 시간 1분으로 늘리기



	5. CloudWatch Event 생성


	- 람다 트리거 지정




![image](https://user-images.githubusercontent.com/43159901/133211681-87c958a1-4d25-4706-987e-27516eafa4ab.png)

