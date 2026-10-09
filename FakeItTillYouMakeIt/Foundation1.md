## When you execute `kubectl apply -f deployment.yaml`, Kubernetes processes your declarative intent through a distributed, event-driven control plane.

---

### Step 1: Authentication, Authorization, & Validation (`kubectl` + API Server)

1. **Local Processing (`kubectl`):**
* `kubectl` parses your YAML locally and validates its client-side structure.
* It sends an HTTP POST or PATCH request containing the desired manifest payload to the **kube-apiserver**.


2. **API Server Request Pipeline:**
* **Authentication & Authorization:** `kube-apiserver` verifies the caller's identity (client certificates, token, or IAM via EKS) and checks RBAC permissions (`can the user create/update deployments in this namespace?`).
* **Mutating Admission Webhooks:** Intercepts the object to modify it if necessary (e.g., sidecar injectors like Istio or custom mutating hooks adding default resource limits/labels).
* **Schema Validation:** Ensures the deployment payload meets the API schema definition.
* **Validating Admission Webhooks:** Evaluates organizational policies (e.g., OPA Gatekeeper/Kyverno checking if images come from approved registries).


3. **Storage (`etcd`):**
* Once validated, `kube-apiserver` writes the desired `Deployment` specification to **etcd** (the cluster's key-value datastore).
* The API Server emits a `Created` / `Updated` event.



---

### Step 2: Deployment Controller (`kube-controller-manager`)

The **Deployment Controller** runs inside `kube-controller-manager` and watches the API server for changes to `Deployment` resources:

1. **Reconciliation Loop:**
* The controller detects the new/updated `Deployment` manifest.


2. **ReplicaSet Creation / Update:**
* Based on the deployment's strategy (e.g., `RollingUpdate`), the Deployment Controller creates or updates a **ReplicaSet**.
* It updates the ReplicaSet’s desired replica count ($N$).


3. **Persisting ReplicaSet:**
* The Deployment Controller posts the ReplicaSet manifest back to `kube-apiserver`, which saves it into `etcd`.



---

### Step 3: ReplicaSet Controller (`kube-controller-manager`)

The **ReplicaSet Controller** watches `ReplicaSet` objects:

1. **Pod Generation:**
* The controller notices that the desired number of Pods ($N$) does not match the currently running Pods ($0$).


2. **Creating Unscheduled Pods:**
* It constructs $N$ individual **Pod spec** manifests using the Pod template defined in the Deployment.
* At this stage, these Pod objects have **no assigned node** (`spec.nodeName` is empty).


3. **Persisting Pods:**
* The ReplicaSet Controller sends these Pod definitions to `kube-apiserver`, which writes them to `etcd`.
* The Pods now enter the **Pending** phase.



---

### Step 4: The Scheduler (`kube-scheduler`)

`kube-scheduler` watches for Pods that have `spec.nodeName == ""`:

1. **Filtering (Predicates):**
* Filters out nodes that cannot run the Pod based on hardware requests (CPU/Memory), taints/tolerations, node selectors, affinity rules, and volume requirements.


2. **Scoring (Priorities):**
* Ranks the remaining capable nodes using scoring plugins (e.g., spreading Pods evenly across availability zones or nodes with existing cached container images).


3. **Binding:**
* Selects the highest-scoring worker node and sends a **Binding** object back to `kube-apiserver`.
* The API Server updates the Pod in `etcd`, setting `spec.nodeName = <selected-node>`.



---

### Step 5: Node Execution (`kubelet` on Worker Node)

The **`kubelet`** running on the target worker node watches the API server for Pods assigned to its node name:

1. **Detecting New Pod Assignment:**
* `kubelet` picks up the newly bound Pod object.


2. **Volume Mounting:**
* If the Pod requires volumes (e.g., ConfigMaps, Secrets, PVCs), `kubelet` coordinates with the CSI (Container Storage Interface) driver to attach and mount the storage onto the node path.


3. **Container Runtime Interface (CRI):**
* `kubelet` invokes the container runtime (e.g., `containerd` or `CRI-O`) via gRPC calls to create the pod sandbox and containers.



---

### Step 6: Network Setup & Container Launch (Runtime + CNI)

1. **Pod Sandbox & Network Namespace:**
* The runtime creates the **pause container** / sandbox environment to hold the shared network namespace (`netns`), IPC, and UTS namespaces.


2. **CNI Provisioning:**
* The runtime calls the **CNI (Container Network Interface)** plugin (e.g., AWS VPC CNI, Calico, Cilium).
* CNI provisions an IP address for the Pod, sets up virtual interfaces (`veth` pair), and configures routing on the host node.


3. **Pulling Images & Creating Containers:**
* The runtime pulls the specified container image(s) from the registry if not already cached.
* It attaches the thin ephemeral writable layer over the read-only image layers.


4. **Starting Process:**
* The low-level runtime (`runc`) uses Linux kernel primitives (`namespaces` and `cgroups`) to launch the application process (`ENTRYPOINT`/`CMD`).



---

### Step 7: Health Checks & Ready State

1. **Probes:**
* `kubelet` runs the defined **Startup Probe** and **Liveness Probe**.
* Once these succeed, `kubelet` runs the **Readiness Probe**.


2. **Marking Ready:**
* When readiness checks pass, `kubelet` reports the container status back to `kube-apiserver`.
* The Pod status transitions from `Pending` $\rightarrow$ `ContainerCreating` $\rightarrow$ **`Running`** (`Ready: True`).


3. **Endpoint Registration:**
* The **EndpointSlice Controller** notices the Pod is `Ready` and adds the Pod's IP to any corresponding Kubernetes `Service` endpoints, allowing network traffic to route to the Pod.

In Kubernetes, the **Startup Probe** and the **Liveness Probe** serve two distinct phases in a container's lifecycle: **initialization** versus **ongoing runtime health**.

Here is why Kubernetes needs both, even if the Startup Probe succeeds:

---

### 1. Different Lifecycles and Roles

* **Startup Probe (Startup Phase):**
Its sole job is to tell Kubernetes: *"Has the application finished booting up and initializing?"*
* Once the Startup Probe succeeds **once**, it **disables itself permanently** for the rest of that container's lifetime.


* **Liveness Probe (Runtime Phase):**
Its job is to continuously check: *"Is the application still alive, or has it deadlocked/frozen in production?"*
* It only starts executing **after** the Startup Probe succeeds, and it runs continuously (e.g., every 10 seconds) until the container stops.



---

### 2. Why the Liveness Probe is Still Needed After Startup Succeeds

Even if an application boots up successfully, runtime failures can occur hours or days later:

* **Deadlocks / Thread Starvation:** A Java application might start perfectly, but later enter a thread deadlock state where the process is running, but it cannot process any incoming requests.
* **Corrupted Memory or Infinite Loops:** A bug might cause a worker process to freeze or hang mid-execution.
* **Stuck Connection Pools:** The app booted fine, but a bug caused all database connection pools to become permanently leaked/exhausted.

In these scenarios, the **Startup Probe is no longer running**, so it cannot detect that the application has broken. The **Liveness Probe** runs repeatedly to catch these runtime freezes and tells `kubelet` to restart the container to recover.

---

### 3. Why Not Just Use a Liveness Probe Alone?

If you only use a Liveness Probe for a slow-starting application (e.g., a legacy app taking 3 minutes to load caches), you face a dilemma:

* If you set the Liveness Probe failure threshold too short, Kubernetes will kill and restart the container **before** it finishes booting, trapping it in a `CrashLoopBackOff`.
* If you set the Liveness Probe delay very long (e.g., 3 minutes) to accommodate slow boots, Kubernetes will take **3 minutes to detect a crash** when the app breaks later in production.

By combining both:

1. **Startup Probe** gives the app a long, flexible window to boot up safely.
2. **Liveness Probe** takes over once boot-up is complete with a fast, aggressive check interval to quickly detect and recover from runtime deadlocks.

While both probes check the health of a container using similar mechanisms (HTTP GET, TCP Socket, Exec command), they trigger completely different actions when they fail:

| Feature | Liveness Probe | Readiness Probe |
| --- | --- | --- |
| **Primary Question** | *"Is the container alive or broken/deadlocked?"* | *"Is the container ready to accept network traffic?"* |
| **Action on Failure** | **Restarts the container** (kills the process and creates a fresh container). | **Removes Pod IP from Endpoints/Service** (stops sending network traffic to it). |
| **Use Case** | Catching unrecoverable states like thread deadlocks, infinite loops, or memory leaks. | Catching transient delays like loading heavy caches, temporary DB disconnections, or overload. |
| **Impact on Pod** | Causes Pod restarts and increases `RESTARTS` count in `kubectl get pods`. | Leaves the Pod running, but sets `READY` status to `0/1` in `kubectl get pods`. |

---

### Detailed Differences

#### 1. Liveness Probe (Recovery Mechanism)

* **Goal:** Detects when an application enters a state where it cannot recover on its own (e.g., a frozen Java process or a broken internal state).
* **Behavior:** When it fails repeatedly (exceeding `failureThreshold`), the `kubelet` restarts the container based on the Pod's `restartPolicy`.
* **Risk of Misconfiguration:** If configured incorrectly or tied to external dependencies (like an unreachable database), it can cause a **restart loop**, repeatedly killing a container that is actually healthy.

#### 2. Readiness Probe (Traffic Routing Mechanism)

* **Goal:** Detects when an application is temporarily unable to serve requests (e.g., warming up caches, executing heavy background tasks, or temporarily lost connection to a backend).
* **Behavior:** When it fails, the **EndpointSlice Controller** removes the Pod's IP address from all matching Kubernetes `Service` endpoints and Ingress controllers. No client traffic will be routed to this Pod until the probe succeeds again.
* **Benefit:** Ensures users never hit a `502 Bad Gateway` or `503 Service Unavailable` error during deployments or temporary traffic spikes.

---

### Summary Rule of Thumb

* Use **Readiness Probe** to protect users from sending traffic to a Pod that isn't ready.
* Use **Liveness Probe** to tell Kubernetes when to "turn it off and on again" via a restart.
