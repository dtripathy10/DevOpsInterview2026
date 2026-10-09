**2. Pod troubleshooting (the core, ~25 min)**

This section covers the most common real-world pod failure modes. Focus on a systematic, layered approach rather than guessing.

### 4. A pod is stuck in Pending. What do you check?

Start with:
```bash
kubectl describe pod <pod-name> -n <namespace>
```
Look at the **Events** section at the bottom — it almost always tells you the reason.

Common causes and what to look for:

| Cause | What you see / check |
|-------|----------------------|
| **Insufficient CPU/memory** | Events: `FailedScheduling` → `0/X nodes are available: Insufficient cpu/memory`. Check `kubectl describe node` or `kubectl top nodes`. Look at requests (not limits). |
| **Taints and tolerations** | Node has a taint the pod doesn’t tolerate (e.g. `node.kubernetes.io/unschedulable`, `NoSchedule` taints on control-plane or dedicated nodes). |
| **Node selectors / affinity / topology spread** | Pod has `nodeSelector`, `nodeAffinity`, or `topologySpreadConstraints` that no node satisfies. |
| **Unbound PersistentVolumeClaim** | Events mention unbound PVC. Check `kubectl get pvc` and the storage class / provisioner. |
| **No nodes in the right Availability Zone / topology** | Especially common with zonal PVCs or topology-aware scheduling. |
| **EKS-specific: pod / IP limit per node** | On EKS with the AWS VPC CNI, each node has a limited number of ENIs/IPs. Events may show `Too many pods` or the scheduler can’t place more pods even when CPU/memory looks fine. Check the max pods per instance type and current pod count. |
| **ResourceQuotas / LimitRanges** | Namespace-level quotas preventing the pod from being created. |
| **PriorityClass / preemption issues** | Rare, but possible with high-priority pods. |

Also verify the scheduler is healthy and that the cluster has Ready nodes.

### 5. A pod is in CrashLoopBackOff. Walk me through it.

1. **Describe the pod**
   ```bash
   kubectl describe pod <pod-name>
   ```
   Look at:
   - **Last State** / **State** → exit code and reason
   - **Restart Count**
   - Events (especially liveness/readiness probe failures)

2. **Check current and previous logs**
   ```bash
   kubectl logs <pod-name> -c <container> --previous
   kubectl logs <pod-name> -c <container>
   ```

3. **Interpret the exit code**
   - **Exit 0** → container exited cleanly (rare in CrashLoop)
   - **Exit 1** → application error / unhandled exception
   - **Exit 137** → OOMKilled (128 + 9). Container exceeded its memory limit.
   - **Exit 127** → command not found (bad entrypoint/cmd or missing binary)
   - **Exit 139** → segmentation fault
   - **Exit 143** → SIGTERM (often from a probe or graceful shutdown)

4. **Common root causes**
   - Bad configuration / missing or wrong secrets / ConfigMaps
   - Application cannot reach a dependency (DB, cache, another service) and crashes on startup
   - Liveness probe is too aggressive and kills a slow-starting but healthy app
   - Wrong command / args
   - Image works locally but fails in-cluster (permissions, missing files, different architecture)

Same mental model as debugging a Docker container that keeps restarting.

### 6. A pod shows ImagePullBackOff or ErrImagePull

```bash
kubectl describe pod <pod-name>
```
Events will show the exact error.

Typical causes:

- **Wrong image name or tag** (typo, non-existent tag, `:latest` that doesn’t exist in the registry)
- **Missing or incorrect `imagePullSecrets`** for private registries
- **Private registry authentication failure**
- **EKS + ECR**: Node IAM role lacks `ecr:GetAuthorizationToken`, `ecr:BatchGetImage`, etc.
- **No outbound internet / missing NAT Gateway or VPC endpoints** from private subnets (very common in locked-down EKS clusters)
- **Docker Hub rate limits** (anonymous pull limits)
- **Image architecture mismatch** (e.g. arm64 image on amd64 node)
- **Registry is down or DNS resolution fails inside the cluster**

Quick checks:
```bash
kubectl get events --field-selector involvedObject.name=<pod-name>
# On the node (if you can): crictl pull <image>
```

### 7. The pod is Running but the app isn’t reachable. How do you find where it breaks?

Use a **layered, hop-by-hop** approach. Never jump straight to the Ingress.

1. **Is the pod actually Ready?**
   ```bash
   kubectl get pod -o wide
   kubectl describe pod → check Readiness probe and Conditions
   ```

2. **Are Service endpoints populated?**
   ```bash
   kubectl get endpoints <service-name>
   kubectl get endpointslices -l kubernetes.io/service-name=<service>
   ```
   Empty endpoints → selector mismatch or pods not Ready.

3. **Port / targetPort correctness**
   - Does the Service `port` / `targetPort` match the containerPort?
   - Is the application actually listening on the expected interface (`0.0.0.0` vs `127.0.0.1`)?

4. **Test from inside the cluster**
   ```bash
   kubectl port-forward pod/<pod-name> 8080:<containerPort>
   # or
   kubectl exec -it <debug-pod> -- curl -v http://<pod-ip>:<port>
   kubectl exec -it <debug-pod> -- curl -v http://<service-name>.<ns>.svc.cluster.local
   ```

5. **NetworkPolicy**
   Check if any NetworkPolicy is denying ingress/egress.

6. **Higher layers**
   - Ingress / ALB / NLB status and target health
   - Security groups / NACL (especially on EKS)
   - DNS resolution inside the cluster

Work from the pod outward. Each successful hop eliminates a layer.

### 8. A pod was OOMKilled, or evicted. What’s the difference, and what do you do?

| Aspect | OOMKilled | Evicted |
|--------|-----------|---------|
| **Who decides** | Linux kernel (cgroup memory limit) | kubelet (node pressure) |
| **Trigger** | Container exceeds its **memory limit** | Node is under memory / disk / PID pressure |
| **Exit code** | 137 | Pod is terminated and usually rescheduled |
| **Scope** | Single container | Affects pods based on QoS and priority |
| **Where to look** | `kubectl describe pod` → Last State: OOMKilled | `kubectl describe node` → Conditions (MemoryPressure, DiskPressure), and Events |

**What to do:**

**For OOMKilled:**
- Check actual usage vs limit (`kubectl top pod`)
- Increase memory limit (and usually the request)
- Look for memory leaks
- Review whether the limit was set too low relative to real usage

**For Eviction:**
- Check node conditions: `kubectl describe node <node>`
- Look at QoS class of the pod (`Guaranteed` > `Burstable` > `BestEffort`)
- Requests vs limits: pods with higher requests are harder to evict
- Consider adding more nodes, adjusting resource requests, or using PriorityClasses / PodDisruptionBudgets

### 9. A rollout is stuck or broke production. What do you do?

**Customer impact first, investigation second.**

Immediate actions:
```bash
kubectl rollout status deployment/<name> -n <ns>
kubectl rollout history deployment/<name>
kubectl rollout undo deployment/<name>          # or --to-revision=N
```

Then investigate:
- Check the new ReplicaSet and its pods
- Why are the new pods not becoming Ready? (readiness probe failures, CrashLoop, ImagePull, etc.)
- Look at the Deployment strategy (`maxUnavailable`, `maxSurge`)
- Events on the Deployment and ReplicaSets
- Compare the previous working ReplicaSet with the new one (`kubectl get rs -o yaml`)

Best practice during an incident:
1. Roll back (or scale the old ReplicaSet back up) to restore service.
2. Only then dig into why the new version failed.

Also useful:
```bash
kubectl get rs -l app=<app> --sort-by=.metadata.creationTimestamp
kubectl describe deploy <name>
```

---

**Interview tip:** Always start with `kubectl describe` + Events, then logs, then work outward (pod → Service → network → higher layers). Showing a calm, layered debugging process is more impressive than memorizing every possible error message.