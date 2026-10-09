A Kubernetes **Service** is an abstract abstraction that provides a stable IP address and DNS name for a set of Pods. Here is how a Service discovers Pods and routes network traffic to them:

---

### 1. How a Service Finds Pods (Discovery via Label Selectors)

1. **Label Matching:**
A Service uses a **label selector** (e.g., `app: my-web-app`) defined in its spec to query the cluster for all matching Pods with the same label key-value pair.
2. **Endpoint / EndpointSlice Generation:**
* Kubernetes runs an **EndpointSlice Controller** in the control plane.
* It constantly watches for Pods matching the Service's selector.
* Whenever Pods are created, deleted, or change status, the controller dynamically creates and updates **EndpointSlice** resources attached to the Service.


3. **Filtering for Readiness:**
* Only Pods that have passed their **Readiness Probes** (`Ready: True`) are added as active IP endpoints in the EndpointSlice.
* If a Pod fails its readiness probe or terminates, its IP is immediately removed from the EndpointSlice, preventing traffic from hitting unready or unhealthy containers.



---

### 2. How Traffic Reaches the Pods (Data Plane Routing)

When a client sends a request to a Service, traffic traverses several networking layers:

#### Step 1: Internal DNS Resolution

* **CoreDNS** runs in the cluster and registers an A/AAAA record for every Service using the format:
`<service-name>.<namespace>.svc.cluster.local`
* The calling application resolves this DNS name to obtain the Service's virtual **ClusterIP**.

#### Step 2: Packet Interception and Load Balancing (`kube-proxy`)

* The Service's **ClusterIP** is a virtual IP—it does not belong to any physical or virtual network interface.
* **`kube-proxy`**, a daemon running on every worker node, manages local network routing rules (typically via `iptables` rules or `IPVS` tables, or kernel-level eBPF with programs like Cilium):
1. A Pod sends traffic to the virtual ClusterIP address on a specific port.
2. As the packet leaves the originating Pod, the node's local network layer intercepts the packet.
3. `kube-proxy` rules perform **DNAT (Destination Network Address Translation)**, replacing the target virtual ClusterIP and Service Port with the actual **Pod IP** and **Container Port** chosen randomly (or via round-robin) from the list of valid EndpointSlices.



#### Step 3: Pod-to-Pod Network Delivery (CNI)

* Once the packet's destination IP is translated to a specific Pod IP, the **CNI (Container Network Interface)** plugin (e.g., AWS VPC CNI, Calico, Flannel) routes the packet across the overlay network or VPC directly to the host node running the destination Pod.
* The packet enters the Pod's isolated network namespace via its virtual ethernet (`veth`) interface and reaches the containerized application process listening on the target port.

---

### Key Support Insight

If a Service is not reaching any application, the most common root cause is a mismatch between the **Service's `spec.selector**` and the **Pod's `metadata.labels**`, or all Pods failing their **readiness probes** (resulting in an empty `kubectl get endpointslices` / `kubectl get endpoints` list).