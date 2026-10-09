An AWS Auto Scaling Group (ASG) creates a new EC2 instance whenever the current capacity falls below the desired capacity, or when an existing instance fails or is replaced. [1, 2, 3] 
## Common Triggers for Creating a New Instance

* Scale-Out Events:
* Dynamic Scaling: CloudWatch alarms trigger a scale-out policy (e.g., CPU utilization exceeds 80%).
   * Scheduled Scaling: A time-based schedule increases the desired capacity.
   * Manual Increase: An administrator manually raises the desired capacity or minimum size of the ASG. [1] 
* Instance Replacement & Healing:
* Health Check Failures: If an instance fails an EC2 status check or an Elastic Load Balancer (ELB) health check, the ASG marks it unhealthy and launches a replacement.
   * Instance Termination: If an instance crashes, gets manually terminated, or is reaped by a Spot market interruption, the ASG spins up a new one to match the target capacity.
   * Maximum Instance Lifetime: When an instance reaches its configured maximum lifetime limit, the ASG replaces it (depending on maintenance policy settings). [3, 4] 
* Updates and Refresher Actions:
* Instance Refresh: During a rolling update or AMI refresh, the ASG launches new instances built from updated launch templates or AMIs before or while terminating old ones.
   * Availability Zone Rebalancing: If you change zone configurations or if capacity drops in a specific zone, the ASG launches instances in other zones to keep the fleet balanced. [5, 6, 7] 

If you are troubleshooting a specific scale-out event, let me know what metrics or policies you have configured on your Auto Scaling Group.

[1] [https://docs.aws.amazon.com](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-lifecycle.html)
[2] [https://docs.aws.amazon.com](https://docs.aws.amazon.com/autoscaling/ec2/userguide/create-your-first-auto-scaling-group.html)
[3] [https://docs.aws.amazon.com](https://docs.aws.amazon.com/autoscaling/ec2/userguide/auto-scaling-groups.html)
[4] [https://docs.aws.amazon.com](https://docs.aws.amazon.com/autoscaling/ec2/userguide/asg-max-instance-lifetime.html)
[5] [https://docs.aws.amazon.com](https://docs.aws.amazon.com/autoscaling/ec2/userguide/instance-refresh-overview.html)
[6] [https://aws.amazon.com](https://aws.amazon.com/blogs/compute/introducing-instance-refresh-for-ec2-auto-scaling/)
[7] [https://aws.amazon.com](https://aws.amazon.com/ec2/autoscaling/faqs/)
