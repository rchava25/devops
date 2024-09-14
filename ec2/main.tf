


resource "aws_instance" "Server" {
     instance_type =var.instance_type_value
     ami = var.ami_value
  
}   