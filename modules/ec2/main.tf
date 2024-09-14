


resource "aws_instance" "webServer" {
     instance_type =var.instance_type_value
     ami = var.ami_value
  
}   