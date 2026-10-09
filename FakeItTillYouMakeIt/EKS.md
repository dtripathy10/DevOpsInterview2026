## 1. Pod gets AccessDenied on S3 or another AWS service

The first question is **which identity is the pod actually using**. Most cases are the pod silently falling back to the node's role.

1. Check what the pod has:
   ```bash
   kubectl exec -it <pod> -- aws sts get-caller-identity
   kubectl get pod <pod> -o jsonpath='{.spec.serviceAccountName}'
   kubectl exec <pod> -- env | grep -E 'AWS_ROLE_ARN|AWS_WEB_IDENTITY|AWS_CONTAINER'
   ```
   If the image has no AWS CLI, use `kubectl debug` with an image that has it. An ARN containing the node role (or `assumed-role/<nodegroup role>`) means the pod isn't getting its own role.
2. **IRSA:**
   - The service account needs the `eks.amazonaws.com/role-arn` annotation.
   - The pod must be created after the annotation was added, so restart it.
   - The IAM role's trust policy must trust the cluster's OIDC provider, with `sub` set to `system:serviceaccount:<namespace>:<sa-name>` and `aud` set to `sts.amazonaws.com`. A typo in the namespace or service account name is the classic failure.
   - The OIDC provider must exist in IAM.
3. **Pod Identity:**
   - The `eks-pod-identity-agent` add-on must be running.
   - Check `aws eks list-pod-identity-associations --cluster-name <c>` for the right namespace and service account.
   - The role trusts `pods.eks.amazonaws.com` with `sts:AssumeRole` and `sts:TagSession`.
4. **Old SDK versions** that don't support web identity or Pod Identity fall back to the node role.
5. If the identity is correct, the problem is permissions: the role's IAM policy, the bucket policy, KMS key policy (for encrypted objects), permission boundaries, SCPs, and VPC endpoint policies. CloudTrail shows the denied call and the reason.

## 2. `kubectl` returns Unauthorized or Forbidden

First split the error type:

- **Unauthorized (401):** authentication failed, so Kubernetes doesn't accept the IAM identity.
- **Forbidden (403):** authenticated, but RBAC doesn't allow that action.
- **Timeout:** a network problem, not a permissions one.

Steps:

1. `aws sts get-caller-identity` shows which IAM identity the user really is. Wrong profile, expired SSO session, or an unassumed role is common.
2. `aws eks update-kubeconfig --name <cluster> --region <region>` to regenerate the config, with the right `--profile` or `--role-arn`.
3. Check how the cluster maps identities: `aws eks describe-cluster --name <c> --query cluster.accessConfig`.
   - **Access entries mode:** `aws eks list-access-entries` and `list-associated-access-policies` for the user's principal.
   - **`aws-auth` ConfigMap mode:** `kubectl -n kube-system get cm aws-auth -o yaml`. The role ARN must match exactly. With SSO roles, the ARN in `aws-auth` must drop the `aws-reserved/sso.amazonaws.com/` path.
4. For Forbidden: `kubectl auth can-i <verb> <resource> -n <ns>` and check RoleBindings and ClusterRoleBindings for the user or group.
5. For timeouts: check the cluster's endpoint access settings. A private-only endpoint is reachable only from the VPC (VPN, bastion, peering), and the endpoint security group must allow the caller.

## 3. Pods can't get IPs, or won't schedule on a node with free CPU

With the AWS VPC CNI, every pod takes a real VPC IP, so IP capacity is a second resource alongside CPU and memory.

1. `kubectl describe pod` shows two distinct symptoms:
   - **Pending with `Too many pods`:** the scheduler says the node is at its max pod count.
   - **ContainerCreating with `FailedCreatePodSandBox` / `failed to assign an IP address`:** the CNI couldn't allocate one.
2. Max pods per node comes from the instance type: roughly ENIs × (IPs per ENI − 1) + 2. Check `kubectl describe node | grep -A8 Allocatable` for `pods:`.
3. Check subnet capacity: `aws ec2 describe-subnets --subnet-ids ... --query 'Subnets[].AvailableIpAddressCount'`.
4. Check CNI logs: `kubectl -n kube-system logs -l k8s-app=aws-node` and `kubectl -n kube-system get pods -l k8s-app=aws-node`.
5. Fixes: enable prefix delegation (`ENABLE_PREFIX_DELEGATION=true`), use larger instances, add subnets or a secondary CIDR with custom networking, and tune warm IP settings if they waste addresses.

## 4. Load balancer not created, or targets unhealthy

1. Check the controller is running: `kubectl -n kube-system get deploy aws-load-balancer-controller` and its logs. Permission errors in the logs usually mean a missing IAM policy on its role.
2. Check the resource is actually handled by it:
   - Ingress needs `ingressClassName: alb` (or the older annotation).
   - A Service needs `loadBalancerClass: service.k8s.aws/nlb` (or the NLB annotations). Without these, a Service of type LoadBalancer may use the legacy in-tree provisioner and create a Classic Load Balancer.
3. `kubectl describe ingress` or `describe svc` shows events with the controller's error.
4. Subnet tags: public subnets need `kubernetes.io/role/elb=1`, internal ones need `kubernetes.io/role/internal-elb=1`.
5. For unhealthy targets:
   ```bash
   aws elbv2 describe-target-health --target-group-arn <arn>
   ```
   The reason code (timeout vs. failed health check) narrows it down. Then verify:
   - Health check path, port, and success codes match what the app returns.
   - Security groups allow traffic from the load balancer to the pod or node port.
   - **Target type:** `ip` goes straight to pods, while `instance` goes through the NodePort.
   - The pod passes its readiness probe, and the Service has endpoints.

## 5. Node is NotReady

1. `kubectl describe node <n>` shows the Conditions (`Ready`, `MemoryPressure`, `DiskPressure`, `PIDPressure`, `NetworkUnavailable`) and recent events. "Kubelet stopped posting node status" means the node isn't communicating.
2. Check the EC2 side: instance state and status checks (system and instance), and console output.
3. Get on the node (SSM Session Manager is the usual way, since SSH is often disabled):
   ```bash
   systemctl status kubelet containerd
   journalctl -u kubelet --since "30 min ago"
   df -h; free -m
   ```
4. Common causes: disk full (images, logs), memory exhaustion, kubelet or containerd crashed, the CNI pod failing, the node unable to reach the API server (security groups, routes, endpoint settings), or the node IAM role missing from access entries or `aws-auth` so it can't join.
5. Mitigate: `kubectl cordon <n>`, then `kubectl drain <n> --ignore-daemonsets --delete-emptydir-data` to move workloads away. Capture logs and console output first, then terminate the instance and let the node group or Karpenter replace it. Replacing is often the right pragmatic fix.

## The pattern a good support engineer follows

For all five, the same habits apply: read events (`describe`) before guessing, confirm which identity or component is actually involved, check one layer at a time, capture evidence before deleting anything, and escalate with a summary of what was checked. That's the thing to score in the interview more than any single command.

I can write broken-app manifests for several of these (wrong IRSA annotation, mismatched Service selector, bad readiness probe, over-requested CPU) if you want hands-on test cases.
