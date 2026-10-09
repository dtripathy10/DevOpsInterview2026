The loop: Inform (see and attribute cost), Optimize (reduce), Operate (make it routine).

1. See it

Tags: team, app, env, owner, enforced and activated for cost allocation
Separate accounts for prod and non-prod
Cost Explorer for quick analysis, CUR with Athena for detail
Budgets and Cost Anomaly Detection for alerts

2. Cut in this order

Waste: unattached EBS, old snapshots, idle load balancers, unused IPs, forgotten dev stacks
Schedule: stop or scale down non-prod outside working hours
Rightsize: Compute Optimizer and CloudWatch utilization data
Pricing: Savings Plans or RIs for the steady baseline, Spot for fault-tolerant work, Graviton
Storage and data: S3 lifecycle and Intelligent-Tiering, gp2 to gp3, log retention
Network: VPC endpoints, fewer cross-AZ calls, CloudFront, NAT review
Architecture: autoscaling, managed or serverless services, caching

3. Make it stick

Teams see their own cost, and own it
Regular cost review, and a unit metric (cost per request, customer, or build)
Cost considered in design review and CI

4. Trade-offs to mention

Commitments can be overbought if usage drops
Spot can be interrupted
Aggressive rightsizing can hurt performance
Non-prod schedules can block late or cross-timezone work
Engineer time has a cost too

Sixty-second answer: “Visibility first, with enforced tags and accounts so cost is attributable. Then act in order of effort: waste, scheduling, rightsizing, pricing models, then architecture. Make it a continuous process with team ownership and unit costs, and balance every saving against reliability.”

If you’d like these as a file you can print or share, such as a doc or a spreadsheet scoring sheet covering the Docker, Kubernetes, and FinOps questions together, tell me the format and I’ll build it.