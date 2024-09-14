provider "aws" {
    region = "us-east-1"
  
}

module "ec2_instance" {
    source = "./modules/ec2"
    ami_value = var.ami_value
    
  
}

output "public_ip" {
    value = module.ec2_instance.webServer_output
  
} 

