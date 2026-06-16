# The Complete Java Backend Interview Question Bank (~200 Q&A) — 5 YOE, India, Targeting 15–20 LPA+

**TL;DR**
- This is a single, exhaustive study document of ~200 of the most commonly asked questions with plain-English model answers, heavily weighted toward scenario-based and coding questions, mapped to 100% of the candidate's resume skills.
- For your target band (15–20 LPA at GCCs, product firms, fintechs, and IT services), expect a 2-round (services) to 3+ round (product/GCC) loop: signature topics are HashMap internals, Java 8 Streams written live, the String-pool memory puzzle, the @Transactional self-invocation pitfall, Kafka consumer-lag debugging, and at least one system-design/LLD problem (URL shortener, rate limiter, BookMyShow, Uber).
- A realistic switch hike from ~11 LPA is 35–50% (≈15–16.5 LPA), and 18–20 LPA is achievable with a services→product/GCC jump plus a competing offer; negotiate total CTC and use a short notice period as leverage.

---

## SECTION 1 — CORE JAVA & OOP (Q1–Q22)

**Q1. What are the four pillars of OOP, with a real example?**
Encapsulation = hiding data behind methods (private fields + getters/setters), e.g. a `BankAccount` keeps `balance` private so nobody sets it directly. Inheritance = reusing a parent's code, e.g. `SavingsAccount extends Account`. Polymorphism = same method behaves differently per type, e.g. `account.calculateInterest()` runs different logic for savings vs current. Abstraction = exposing what something does, not how, e.g. coding to a `PaymentGateway` interface. Trade-off: inheritance creates tight coupling, so I favor composition over inheritance in real services.

**Q2. equals() and hashCode() — what's the contract?**
If two objects are equal by `equals()`, they MUST return the same `hashCode()`. The reverse isn't required (same hash, may not be equal — that's a collision). If you override one you must override the other, otherwise HashMap/HashSet break — you could put a key in and never find it again. Example: two `Employee` objects with the same `id` should be equal and hash the same.

**Q3. Why are Strings immutable in Java?**
Once created, a String's value can't change. Reasons: security (file paths, DB URLs can't be tampered with after a check), thread-safety (shareable without locks), and the String pool (literals are cached and reused). Any "modification" creates a new object. Example: `s.concat("x")` returns a new String; the old one is unchanged.

**Q4. String pool — explain the s1/s2/s3 memory puzzle. (JPMorgan signature)**
`String s1 = "Kailash"; String s2 = "Kailash"; String s3 = new String("Kailash");` — `s1` and `s2` point to the SAME pooled object (one allocation), so `s1 == s2` is true. `new String(...)` forces a brand-new heap object, so `s3 == s1` is false even though `s3.equals(s1)` is true. So there are effectively two objects: one in the pool, one in the heap.

**Q5. String vs StringBuilder vs StringBuffer?**
String is immutable — use for constants. StringBuilder is mutable and fast but not thread-safe — use for heavy string building in one thread (e.g. building a CSV in a loop). StringBuffer is the synchronized (thread-safe) version, slightly slower — use only when multiple threads share it. Rule of thumb: loops that concatenate should use StringBuilder, never `+`.

**Q6. final vs finally vs finalize?**
`final` is a keyword: a final variable can't be reassigned, a final method can't be overridden, a final class can't be extended. `finally` is a block that always runs after try/catch — used to close resources. `finalize()` was a method called before garbage collection (now deprecated; use try-with-resources instead). They're unrelated despite the similar names.

**Q7. Checked vs unchecked exceptions?**
Checked exceptions (e.g. `IOException`, `SQLException`) must be declared or caught — they represent recoverable problems the caller should handle. Unchecked (RuntimeException like `NullPointerException`, `IllegalArgumentException`) are programming bugs and don't need declaring. Trade-off: I use unchecked exceptions for business validation in services so I don't pollute every signature with `throws`.

**Q8. What's in the Object class?**
Every class extends Object, so all objects get `equals()`, `hashCode()`, `toString()`, `getClass()`, `clone()`, `wait()`, `notify()`, `notifyAll()`, and `finalize()`. We commonly override `equals`, `hashCode`, and `toString`.

**Q9. Abstract class vs interface — when do you use each?**
Use an abstract class when classes share state and common code (a base `Shape` with a stored `name`). Use an interface for a capability/contract that unrelated classes can implement (`Comparable`, `Runnable`). A class can implement many interfaces but extend only one class. Since Java 8 interfaces can have default methods, so the line blurred, but interfaces still can't hold instance state.

**Q10. Overloading vs overriding?**
Overloading = same method name, different parameters, same class — resolved at compile time (e.g. `print(int)` and `print(String)`). Overriding = subclass redefines a parent method with the same signature — resolved at runtime (dynamic dispatch). Overriding powers polymorphism.

**Q11. Explain JVM, JRE, JDK.**
JDK = tools to develop (compiler `javac`, debugger) + JRE. JRE = what you need to run (JVM + libraries). JVM = the engine that executes bytecode and gives "write once, run anywhere." Flow: `.java` → `javac` → `.class` bytecode → JVM runs it on any OS.

**Q12. Walk me through JVM memory areas.**
Heap = all objects, shared across threads, where GC works. Stack = per-thread, holds method frames and local variables/references (LIFO). Metaspace = class metadata (replaced PermGen in Java 8). PC register and native stacks exist too. Example: `new Order()` lives on the heap; the reference variable lives on the stack. Infinite recursion blows the stack (`StackOverflowError`); too many live objects blow the heap (`OutOfMemoryError`).

**Q13. How does garbage collection work?**
GC automatically frees objects no longer reachable from "roots" (stack variables, statics). The heap is split into Young (Eden + Survivor) and Old generations. Most objects die young and are collected cheaply (minor GC); survivors get promoted to Old (major GC). Modern collectors: G1 (default), and ZGC/Shenandoah for low pause times. You don't free memory manually; you just remove references.

**Q14. Scenario: memory keeps growing and you suspect a leak. How do you debug?**
First confirm via monitoring (heap trending up, frequent full GCs, rising old-gen). Take a heap dump (`jmap`, or automatically with `-XX:+HeapDumpOnOutOfMemoryError`) and analyze in Eclipse MAT to find the dominant retained objects. Common culprits: static collections that never clear, unbounded caches, ThreadLocals not removed in thread pools, listeners not unregistered. Fix the root reference, add bounds (e.g. an LRU cache), and re-test.

**Q15. What is immutability and how do you build an immutable class?**
Make the class `final`, all fields `private final`, set them only in the constructor, provide no setters, and for mutable fields (like a List) make defensive copies on the way in and out. Benefit: inherently thread-safe and safe as a Map key. Example: Java's `String` and `LocalDate`.

**Q16. Pass-by-value or pass-by-reference?**
Java is always pass-by-value. For objects, the value passed is a copy of the reference, so the method can change the object's internal state but cannot repoint the caller's variable. Example: inside a method `list.add(x)` is visible to the caller, but `list = new ArrayList<>()` is not.

**Q17. static keyword — what does it mean?**
`static` belongs to the class, not an instance — one shared copy. Static variables are class-level state; static methods can be called without an object (`Math.max`); static blocks run once at class load. Caution: static mutable state is a common source of concurrency bugs.

**Q18. Can you serialize everything? What about transient/static fields? (Cognizant signature)**
To serialize, implement `Serializable`. `transient` fields are skipped (e.g. passwords, caches). `static` fields belong to the class, not the object, so they're not serialized either. `serialVersionUID` is a version stamp; if it doesn't match on deserialization you get `InvalidClassException` — so set it explicitly to control compatibility.

**Q19. What is autoboxing and a gotcha with it?**
Autoboxing auto-converts between primitives and wrappers (`int` ↔ `Integer`). Gotcha: `Integer` caches −128 to 127, so `Integer a=127, b=127; a==b` is true but at 128 it's false — always compare wrappers with `.equals()`. Also unboxing a null `Integer` throws NPE.

**Q20. What does the `volatile` keyword do? (Cognizant signature)**
`volatile` guarantees visibility: a write by one thread is immediately seen by others because reads/writes go to main memory, not a CPU cache. It also prevents instruction reordering around it. But it does NOT make compound actions (like `count++`) atomic — for that use `synchronized` or `AtomicInteger`. Good use: a `volatile boolean running` flag to stop a thread.

**Q21. What is the difference between `==` and `equals()`?**
`==` compares references (are they the same object?) for objects, and values for primitives. `equals()` compares logical equality as defined by the class. For Strings, always use `equals()` for content comparison.

**Q22. enum — give a real use case. (Cognizant signature)**
An enum is a fixed set of constants and can have fields/methods. Use it for states or types: `enum OrderStatus { CREATED, PAID, SHIPPED }`. Bonus: enum is the simplest thread-safe Singleton in Java because the JVM guarantees one instance.

---

## SECTION 2 — JAVA 8+ AND MODERN JAVA (Q23–Q40)

**Q23. What did Java 8 add and why does it matter?**
Lambdas, the Stream API, functional interfaces, `Optional`, default methods, method references, and a new Date/Time API. It made code more declarative and concise — you describe *what* you want (filter, map, collect) instead of writing loops.

**Q24. What is a functional interface?**
An interface with exactly one abstract method, so it can be a lambda target. Examples: `Runnable`, `Comparator`, and the `java.util.function` set — `Function`, `Predicate`, `Consumer`, `Supplier`. The `@FunctionalInterface` annotation enforces the single-method rule.

**Q25. Live coding: sort a List of Employees by id, then filter and collect. (Cognizant/Accenture signature)**
`employees.stream().sorted(Comparator.comparingInt(Employee::getId)).collect(Collectors.toList());` To filter salary > 50000 then get names: `.stream().filter(e -> e.getSalary() > 50000).map(Employee::getName).collect(Collectors.toList())`. Streams read top-to-bottom like a pipeline.

**Q26. JPMorgan signature: given an array, remove odd numbers, multiply each remaining by a constant, return the sum — using Streams.**
`Arrays.stream(arr).filter(n -> n % 2 == 0).map(n -> n * k).sum();` It reads exactly like the requirement: filter evens, multiply, sum. `IntStream` avoids boxing.

**Q27. map vs flatMap?**
`map` transforms each element 1-to-1 (`String` → its length). `flatMap` flattens nested structures — each element becomes a stream and they're merged into one. Example: a `List<List<String>>` → one flat `List<String>` via `flatMap(List::stream)`. Use flatMap whenever a mapping produces a collection/stream you want flattened.

**Q28. What is Optional and how do you use it well?**
`Optional` is a container that may or may not hold a value — it makes "no result" explicit instead of returning null. Use `orElse`, `orElseGet`, `map`, `ifPresent`. Anti-pattern: calling `.get()` without checking, or using Optional for fields/parameters. Good use: repository methods returning `Optional<User>`.

**Q29. Intermediate vs terminal stream operations?**
Intermediate ops (`filter`, `map`, `sorted`) are lazy and return a stream — nothing runs yet. Terminal ops (`collect`, `forEach`, `reduce`, `count`) trigger execution. A stream can be consumed only once.

**Q30. When do parallel streams help, and when do they hurt?**
`parallelStream()` splits work across the common ForkJoinPool. They help for large, CPU-bound, independent work on data structures that split well (arrays). They hurt for small datasets, IO-bound work, or when the lambda has shared mutable state (race conditions) — and they can starve the shared pool. I rarely use them for IO; for that I use CompletableFuture with a dedicated executor.

**Q31. default and static methods in interfaces — why were they added?**
Default methods let you add new methods to an interface without breaking existing implementers (that's how `Collection.stream()` was added). Static methods group utility logic on the interface. Trade-off: if two interfaces give conflicting defaults, the class must override and resolve it.

**Q32. What are records (Java 16)?**
Records are immutable data carriers — `record Point(int x, int y) {}` auto-generates the constructor, accessors (getters), `equals`, `hashCode`, and `toString`. Great for DTOs and value objects. They cut boilerplate massively.

**Q33. What are sealed classes (Java 17)?**
A sealed class/interface restricts which classes can extend/implement it via `permits`. Example: `sealed interface Shape permits Circle, Rectangle`. It gives you a closed set so the compiler can check exhaustive switches — useful for domain modeling.

**Q34. What are virtual threads (Java 21)?**
Per JEP 444 (finalized in JDK 21), virtual threads are lightweight threads managed by the JVM, not the OS, that "dramatically reduce the effort of writing, maintaining, and observing high-throughput concurrent applications." The JVM schedules many virtual threads (M:N) onto a small pool of "carrier" platform threads and keeps their stacks on the heap, so you can run millions cheaply. They let you write simple blocking, thread-per-request IO code that still scales — a big win for IO-heavy backends. Platform (OS) threads stay best for CPU-bound work.

**Q35. method references — the four kinds?**
Shorthand for lambdas: static (`Integer::parseInt`), instance of a particular object (`System.out::println`), instance of an arbitrary object (`String::toLowerCase`), and constructor (`ArrayList::new`).

**Q36. Collection vs Stream? (Accenture signature)**
A Collection stores and lets you add/remove elements — it's about data. A Stream is a one-time computation pipeline over data — it doesn't store anything and can't be reused. You go Collection → stream → process → back to Collection.

**Q37. reduce() — what does it do?**
`reduce` combines stream elements into one result using an accumulator. Example: sum = `stream.reduce(0, Integer::sum)`. Useful for folding (sum, max, concatenation).

**Q38. How do you group and count with Streams?**
`Collectors.groupingBy` plus `counting`: `words.stream().collect(Collectors.groupingBy(w -> w, Collectors.counting()))` gives a frequency map. `partitioningBy` splits into true/false buckets.

**Q39. What is the new Date/Time API?**
Java 8's `java.time` (`LocalDate`, `LocalDateTime`, `Instant`, `Duration`) is immutable and thread-safe, replacing the buggy, mutable `Date`/`Calendar`. Use `LocalDate.now()`, `plusDays()`, etc.

**Q40. What is a Predicate and how do you combine them?**
A `Predicate<T>` returns boolean. Combine with `.and()`, `.or()`, `.negate()`: `isActive.and(isAdult)`. Used heavily in `filter`.

---

## SECTION 3 — COLLECTIONS (Q41–Q52)

**Q41. How does HashMap work internally? (near-universal)**
A HashMap is an array of buckets. On `put`, it computes the key's `hashCode()`, spreads it (`hash ^ (hash >>> 16)`), and maps it to a bucket index. Collisions (same bucket) form a linked list. On `get`, it goes to the bucket and uses `equals()` to find the key. Default capacity 16 (`DEFAULT_INITIAL_CAPACITY = 1<<4`), load factor 0.75 (`DEFAULT_LOAD_FACTOR = 0.75f`) — when 75% full it doubles and rehashes.

**Q42. What is treeification in HashMap? (Java 8+)**
Per the OpenJDK source, when a single bucket's linked list reaches `TREEIFY_THRESHOLD = 8` nodes AND the table size is at least `MIN_TREEIFY_CAPACITY = 64`, that list converts to a red-black tree, dropping worst-case lookup in that bucket from O(n) to O(log n). If a bin shrinks below `UNTREEIFY_THRESHOLD = 6` it converts back to a list. (Below capacity 64, Hibernate-style heavy collisions trigger a resize instead of treeification.) This protects against hash-collision attacks and bad hash functions.

**Q43. ConcurrentHashMap — how is it thread-safe?**
Since Java 8 it dropped segment locking and uses CAS for the first insert into a bucket plus fine-grained `synchronized` locking on the individual bucket head — so different buckets can be written concurrently. Reads are lock-free (the table is `volatile`). It allows no null keys/values. Far more scalable than `Hashtable` or `Collections.synchronizedMap`, which lock the whole map.

**Q44. ArrayList vs LinkedList?**
ArrayList is a resizable array: O(1) random access, but inserting/removing in the middle is O(n) due to shifting. LinkedList is a doubly-linked list: O(1) add/remove at ends, but O(n) access by index. In practice ArrayList wins almost always because of CPU cache locality; I use LinkedList only for queue/deque patterns.

**Q45. HashMap vs Hashtable vs ConcurrentHashMap?**
HashMap: not synchronized, allows one null key, fastest single-thread. Hashtable: legacy, fully synchronized, no nulls — avoid. ConcurrentHashMap: thread-safe with high concurrency, no nulls — the modern choice for shared maps.

**Q46. Comparable vs Comparator? (Cognizant/Accenture signature)**
`Comparable` defines the natural ordering inside the class via `compareTo` (one ordering, e.g. by id). `Comparator` is external — you write separate ordering logic via `compare`, and you can have many (by name, by salary). Use Comparable for the default sort, Comparators for everything else: `list.sort(Comparator.comparing(Employee::getName))`.

**Q47. fail-fast vs fail-safe iterators?**
Fail-fast iterators (ArrayList, HashMap) throw `ConcurrentModificationException` if the collection is structurally modified during iteration. Fail-safe iterators (CopyOnWriteArrayList, ConcurrentHashMap) work on a copy/snapshot and don't throw, but may not see the latest changes. To remove during iteration safely, use the iterator's own `remove()`.

**Q48. Set types — HashSet vs LinkedHashSet vs TreeSet?**
HashSet: no order, O(1), backed by HashMap. LinkedHashSet: keeps insertion order. TreeSet: sorted order, O(log n), backed by a red-black tree. Choose by whether you need ordering and at what cost.

**Q49. How does HashSet store uniqueness?**
A HashSet is backed by a HashMap where your element is the key and a dummy constant is the value — so uniqueness uses the same `hashCode`/`equals` mechanism.

**Q50. Why must HashMap keys be immutable? (Paytm manager round)**
If a key's fields change after insertion, its `hashCode` changes, so the map looks in a different bucket and can't find the entry — it effectively gets lost. That's why `String` and wrapper types make ideal keys. For a custom key, make it immutable and override `equals`/`hashCode`.

**Q51. What's the difference between Iterator and ListIterator?**
Iterator goes forward only and supports `remove`. ListIterator (for lists) goes both directions and supports `add`/`set` plus index access.

**Q52. How do you make a collection thread-safe / read-only?**
Thread-safe: `Collections.synchronizedList()` or concurrent collections. Read-only: `Collections.unmodifiableList()` or `List.of()`. The concurrent collections scale better than the synchronized wrappers.

---

## SECTION 4 — MULTITHREADING & CONCURRENCY (Q53–Q68)

**Q53. synchronized vs ReentrantLock?**
`synchronized` is a keyword with automatic lock release when the block exits — simple but limited. `ReentrantLock` is a class giving more control: `tryLock()` with timeout, interruptible locking, fairness, and multiple condition variables. Trade-off: ReentrantLock must be unlocked manually in a `finally`, or you leak the lock. I default to synchronized and reach for ReentrantLock when I need tryLock/timeouts.

**Q54. What is a deadlock and how do you prevent it?**
Deadlock = two threads each holding a lock the other needs, so both wait forever. Prevent it by always acquiring locks in the same global order, using `tryLock` with a timeout, and keeping critical sections small. Detect it in production by taking a thread dump (`jstack`) and looking for the deadlock section / BLOCKED threads in a cycle.

**Q55. Runnable vs Callable?**
Runnable's `run()` returns nothing and can't throw checked exceptions. Callable's `call()` returns a value and can throw checked exceptions — used with ExecutorService, returning a `Future`. Use Callable when you need a result back from the task.

**Q56. What is the Executor framework / thread pool, and why use it?**
ExecutorService manages a pool of reusable threads so you don't create/destroy threads per task (expensive). `Executors.newFixedThreadPool(n)` is common. You submit tasks and get Futures. Always `shutdown()` the pool. Best practice: separate pools for CPU-bound vs IO-bound work, bounded queues, and a sensible rejection policy.

**Q57. Explain CompletableFuture with a real use. (scenario)**
CompletableFuture runs async work and chains steps without blocking. Scenario — fetch a product's price from three sites in parallel and combine: kick off three `supplyAsync` calls, combine with `allOf`, and time-box with `get(5, SECONDS)` so a slow site can't hang the request. Always pass an explicit executor to `*Async` methods so you don't starve the common pool, and use `exceptionally` to handle failures.

**Q58. What does volatile guarantee that synchronized also does — and what's the difference?**
Both give visibility (changes seen across threads). synchronized additionally gives mutual exclusion (atomicity of the block) and is heavier. volatile is lighter but only for single reads/writes, not compound operations. Use volatile for flags, synchronized/locks for multi-step updates.

**Q59. What are atomic classes and CAS?**
`AtomicInteger`, `AtomicLong`, etc. provide lock-free atomic operations using Compare-And-Swap: the CPU compares the current value to an expected value and swaps only if they match, retrying otherwise. Great for counters under contention — `incrementAndGet()` is atomic without locks.

**Q60. Explain the Java Memory Model and happens-before.**
The JMM defines when one thread's writes become visible to another. "Happens-before" is the ordering guarantee: if action A happens-before B, A's effects are visible to B. Key edges: unlock → subsequent lock, volatile write → volatile read, `Thread.start()` → the thread's work, the thread's work → `join()`. Without a happens-before edge, there's no visibility guarantee.

**Q61. What is ThreadLocal and a common pitfall?**
ThreadLocal gives each thread its own copy of a variable — useful for non-thread-safe but expensive objects like `SimpleDateFormat`, or for carrying request context. Pitfall: in a thread pool the thread is reused, so if you don't `remove()` the value you get stale data and memory leaks. Always clean up in a `finally`.

**Q62. Implement a producer-consumer. (scenario/coding)**
Use a `BlockingQueue` (e.g. `LinkedBlockingQueue`) — the producer calls `put()` (blocks when full, giving natural backpressure) and the consumer calls `take()` (blocks when empty). The queue handles all the wait/notify internally, so the code stays clean and safe.

**Q63. Why call start() instead of run()?**
`start()` creates a new thread and the JVM calls `run()` on it. Calling `run()` directly just runs it on the current thread — no concurrency.

**Q64. wait/notify/notifyAll — what are they for?**
They coordinate threads on an object's monitor. `wait()` releases the lock and pauses until `notify()`/`notifyAll()` wakes it. Always call them inside `synchronized` and wait in a loop checking the condition (to handle spurious wakeups). Higher-level tools (BlockingQueue, CountDownLatch) usually replace them.

**Q65. Scenario: how do you make thread T2 run after T1, and T3 after T2?**
Use `join()`: start T1, call `t1.join()`, then start T2, `t2.join()`, then T3. `join` makes the current thread wait for the other to finish.

**Q66. What is a race condition and how do you fix it?**
A race condition is when the result depends on thread timing because threads read-modify-write shared state without coordination. Fix with synchronization, atomic classes, or immutable/confined state. Classic example: two threads doing `count++` losing updates — fix with AtomicInteger.

**Q67. CountDownLatch vs CyclicBarrier?**
CountDownLatch: one or more threads wait until a count reaches zero — one-time use (e.g. wait for 3 services to warm up). CyclicBarrier: a set of threads wait for each other at a barrier point and it resets for reuse (e.g. parallel phases).

**Q68. Scenario: a long-running task is blocking request threads. What do you do?**
Move it off the request thread: submit it to a dedicated ExecutorService or use `CompletableFuture` / `@Async`, so the web thread returns quickly. For very high IO concurrency on Java 21, virtual threads also help. Add timeouts and a bounded queue so the background work can't grow unbounded.

---

## SECTION 5 — SPRING & SPRING BOOT (Q69–Q88)

**Q69. What is IoC and Dependency Injection?**
Inversion of Control means Spring creates and wires your objects instead of you doing `new`. Dependency Injection is how it supplies dependencies — usually constructor injection. Benefit: loose coupling and easy testing (inject mocks). Example: a controller gets its service injected rather than constructing it.

**Q70. BeanFactory vs ApplicationContext?**
Both are IoC containers. BeanFactory is basic and lazy. ApplicationContext extends it with eager singleton creation, event publishing, i18n, and annotation support — it's what Spring Boot uses. Always use ApplicationContext in real apps.

**Q71. Explain the Spring bean lifecycle.**
Spring instantiates the bean, injects dependencies, calls aware interfaces, runs `@PostConstruct` (and `BeanPostProcessor` hooks), the bean is used, then on shutdown runs `@PreDestroy`. Hook points let you initialize resources and clean them up.

**Q72. What are bean scopes?**
Singleton (default — one instance per container), prototype (new instance each request), and for web: request, session, application. Caution: injecting a prototype/request bean into a singleton needs a proxy or provider, or you get the same instance.

**Q73. Stereotype annotations — @Component, @Service, @Repository, @Controller?**
All are `@Component` specializations picked up by component scanning. `@Service` marks business logic, `@Repository` marks data access (and translates DB exceptions), `@Controller`/`@RestController` handle web requests. They're mostly semantic but `@Repository`'s exception translation is functional.

**Q74. How does Spring Boot auto-configuration work?**
Boot scans the classpath and, via `@EnableAutoConfiguration`, applies sensible configuration conditionally (`@ConditionalOnClass`, `@ConditionalOnMissingBean`). If it sees the H2 jar, it configures an in-memory DB; if you define your own bean, it backs off. That's why "starters" + minimal config just work.

**Q75. @Controller vs @RestController? (Accenture/Wipro signature)**
`@RestController` = `@Controller` + `@ResponseBody`, so every method returns data (JSON) directly instead of a view name. Use `@RestController` for REST APIs and `@Controller` for server-rendered pages.

**Q76. Spring vs Spring Boot? (Infosys/Wipro signature)**
Spring is the core framework but needs lots of manual configuration and an external server. Spring Boot sits on top with auto-configuration, embedded Tomcat/Jetty, starter dependencies, and production features (Actuator) — so you "just code and run." Spring Boot doesn't replace Spring; it removes the boilerplate.

**Q77. Explain @Transactional propagation. (very common)**
Propagation controls how a transaction joins or starts. REQUIRED (default) joins an existing one or creates one. REQUIRES_NEW suspends the outer and starts an independent transaction (good for audit logs that must persist even if the business txn rolls back). NESTED uses a savepoint inside the outer. Most code only needs REQUIRED and REQUIRES_NEW.

**Q78. The @Transactional self-invocation pitfall — explain it. (high-signal)**
`@Transactional` works through a Spring proxy. If method A calls method B in the SAME class via `this.B()`, the call bypasses the proxy, so B's `@Transactional` is ignored — no new transaction. Fixes: move B to another bean, or self-inject the proxy. Two related pitfalls: it's silently ignored on private/non-public methods, and by default it only rolls back on RuntimeException/Error — for checked exceptions add `rollbackFor = Exception.class`.

**Q79. Explain isolation levels.**
They control what concurrent transactions can see: READ_UNCOMMITTED (dirty reads), READ_COMMITTED (no dirty reads — common default), REPEATABLE_READ (no non-repeatable reads), SERIALIZABLE (full isolation, slowest). Higher isolation = more consistency, less concurrency.

**Q80. What is AOP and where do you use it?**
Aspect-Oriented Programming factors out cross-cutting concerns (logging, security, transactions) into aspects applied via proxies, so business code stays clean. Spring itself uses AOP for `@Transactional` and method security. You write an aspect with a pointcut and advice (`@Before`, `@Around`).

**Q81. How do you do global exception handling?**
Use `@RestControllerAdvice` with `@ExceptionHandler` methods to map exceptions to clean HTTP responses in one place — e.g. a `ResourceNotFoundException` → 404 with a standard error body. Keeps controllers free of try/catch and gives consistent error contracts.

**Q82. What is Spring Boot Actuator?**
Actuator exposes production endpoints — `/actuator/health`, `/metrics`, `/info`, `/beans` — for monitoring and ops. The health endpoint also feeds Kubernetes liveness/readiness probes. Secure these endpoints in production.

**Q83. @Qualifier and @Primary — what problem do they solve?**
When multiple beans of the same type exist, Spring can't choose. `@Primary` marks the default; `@Qualifier("name")` picks a specific one at the injection point. Together they resolve ambiguity.

**Q84. How do circular dependencies happen and how do you fix them?**
Bean A needs B and B needs A at construction time. Spring can't build either. Fixes: redesign to remove the cycle (best), use setter/field injection for one side, or `@Lazy`. With constructor injection a cycle fails fast at startup — which is good.

**Q85. RestTemplate vs WebClient vs Feign?**
RestTemplate is the old blocking HTTP client (maintenance mode). WebClient is the modern non-blocking, reactive client (works blocking too). Feign is a declarative client — you define an interface and Spring Cloud implements the HTTP calls, cleanest for microservice-to-microservice calls. I prefer Feign for inter-service calls and WebClient when I need async/streaming.

**Q86. What are profiles?**
`@Profile` and `application-{profile}.properties` let you load different config per environment (dev, qa, prod). Activate with `spring.profiles.active`. Keeps environment-specific values out of code.

**Q87. How do you externalize configuration?**
Via `application.properties/yml`, environment variables, command-line args, and config servers. Spring's order of precedence lets env vars/CLI override files — handy for containers. Use `@ConfigurationProperties` to bind groups of properties to a typed object.

**Q88. Scenario: the app is slow. How do you debug it as a Spring Boot service? (very common)**
Start from metrics (Actuator/Micrometer + Grafana): is it CPU, memory, GC, DB, or downstream calls? Check slow DB queries (enable SQL logging, look for N+1), thread dumps for blocked threads, connection pool exhaustion (HikariCP), and external latency. Add caching for hot reads, fix the N+1, tune the pool, and add timeouts/circuit breakers on downstream calls. Validate with load testing.

---

## SECTION 6 — SPRING SECURITY & JWT (Q89–Q98)

**Q89. How does the Spring Security filter chain work?**
Security is a chain of servlet filters in front of your controllers. Each request passes through filters that handle authentication, authorization, CSRF, etc. Key filters: `UsernamePasswordAuthenticationFilter`, `BasicAuthenticationFilter`, and your custom JWT filter. Order matters — you authenticate before authorizing.

**Q90. Walk me through end-to-end JWT auth.**
User logs in with credentials → server validates and returns a signed JWT. The client sends it in the `Authorization: Bearer <token>` header on every request. A custom `OncePerRequestFilter` extracts the token, validates the signature and expiry, loads the user, and sets the `SecurityContext`. Because it's stateless, no server session is stored.

**Q91. What's inside a JWT?**
Three dot-separated Base64 parts: header (algorithm/type), payload (claims like user, roles, expiry), and signature. The signature (HMAC with a secret, or RSA with a private key) ensures it wasn't tampered with. Note: the payload is encoded, not encrypted — never put secrets in it.

**Q92. Access token vs refresh token?**
The access token is short-lived (minutes) and sent on each request. The refresh token is long-lived (days) and stored securely; when the access token expires, the client uses the refresh token to get a new one without re-login. This limits the damage if an access token leaks.

**Q93. Scenario: JWT is stateless, so how do you log a user out / revoke a token?**
Since JWTs can't be "deleted," options are: keep access tokens short-lived and revoke refresh tokens; maintain a token blacklist/denylist in Redis checked per request; or rotate the signing key to invalidate everything. Most teams use short access tokens + a refresh-token store.

**Q94. How do you do method-level authorization?**
Enable it and use `@PreAuthorize("hasRole('ADMIN')")` or SpEL like `@PreAuthorize("#userId == authentication.principal.id")`, plus `@PostFilter` to filter returned collections. Note the same proxy/self-invocation caveat as @Transactional applies.

**Q95. How do you secure a stateless REST API?**
Use HTTPS, stateless session policy, JWT/OAuth2 bearer tokens validated by a filter, role-based `authorizeHttpRequests` rules, disable CSRF (safe because you're not using cookies), tight CORS (allow only trusted origins), and store passwords hashed.

**Q96. CSRF — what is it and when do you disable it?**
CSRF tricks a logged-in browser into making unwanted requests using its cookies. Spring protects state-changing requests with a synchronizer token. Disable CSRF only for stateless APIs that use bearer tokens in headers (not cookies), since there's no cookie to exploit.

**Q97. How do you store passwords?**
Never plaintext. Hash with a slow, salted algorithm — `BCryptPasswordEncoder` is the standard. BCrypt automatically generates and embeds a per-password salt and is intentionally slow (cost factor) to resist brute force; raise the strength as hardware improves.

**Q98. What is OAuth2 and how does it relate to JWT?**
OAuth2 is an authorization framework: an authorization server issues tokens, a resource server validates them. The access token is often a JWT. It enables delegated access (login with Google) and SSO. Spring Security has first-class resource-server and client support.

---

## SECTION 7 — APACHE KAFKA (Q99–Q112)

**Q99. Explain Kafka's architecture.**
Producers publish to topics; topics split into partitions for parallelism; brokers store partitions; consumers read in consumer groups where each partition is read by exactly one consumer in the group. Offsets track read position; replication copies partitions across brokers for fault tolerance.

**Q100. How does Kafka guarantee ordering?**
Ordering is guaranteed only within a partition, not across partitions. To keep related events ordered (e.g. all events for one order), use the same key so they land in the same partition. Trade-off: ordering vs parallelism.

**Q101. Explain delivery semantics: at-most-once, at-least-once, exactly-once.**
At-most-once: may lose messages, never duplicates (commit offset before processing). At-least-once: never loses, may duplicate (process then commit) — the common default. Exactly-once: no loss, no duplicates, via idempotent producer + transactions. Choose by cost: payments need exactly-once or idempotent consumers; analytics tolerate at-least-once.

**Q102. What does the acks setting do?**
It's the durability/latency trade-off. `acks=0`: fire-and-forget, fastest, can lose data. `acks=1`: wait for the leader only. `acks=all` (-1): wait for all in-sync replicas — strongest guarantee against loss. For important data use `acks=all` + replication.

**Q103. How do you achieve idempotency / exactly-once?**
Set `enable.idempotence=true` so producer retries don't create duplicates, and use the transactional API to atomically write output and commit consumer offsets. Even then, downstream duplicates can occur if you commit offsets before the DB write — so commit AFTER the write, or make the consumer idempotent (upserts).

**Q104. Scenario: consumer lag is high and growing. How do you diagnose and fix it?**
Lag = difference between latest produced offset and committed offset. Check whether one consumer owns more/heavier partitions, whether processing is slow (DB calls, heavy CPU), or `max.poll.records` is too high causing timeouts. Fixes: add consumers up to the partition count, increase partitions, speed up or batch processing, move heavy work off the poll loop, and scale resources. Monitor with Burrow/Kafka Lag Exporter.

**Q105. What is consumer group rebalancing and why is it a problem?**
When a consumer joins/leaves, the group coordinator reassigns partitions — during which consumption pauses ("stop the world"). Frequent rebalances hurt throughput. Mitigate with cooperative-sticky rebalancing (default 2.4+), static membership (great in Kubernetes), and tuned session timeouts so a slow consumer isn't wrongly kicked out.

**Q106. What is a Dead Letter Queue and when do you use it?**
A DLQ is a separate topic where messages that repeatedly fail processing are parked, so one poison message doesn't block the partition. You alert on it and reprocess later after fixing the bug. Often paired with retry topics with backoff.

**Q107. How do you decide the number of partitions?**
Partitions set max consumer parallelism (consumers ≤ partitions). More partitions = more throughput but more file handles, more memory, and slower rebalances/leader elections. Size for expected peak parallelism with headroom; you can add partitions later but it can disturb key-based ordering.

**Q108. What are ISR and replication factor?**
Replication factor = copies of each partition (commonly 3). ISR (in-sync replicas) are the replicas fully caught up to the leader; a write with `acks=all` is acknowledged only when all ISR have it. If the leader dies, an ISR becomes leader — no data loss.

**Q109. Scenario: you see duplicate messages in your DB even with idempotent producers. Why?**
Idempotent producers only stop duplicates on the Kafka write side. Downstream duplicates happen when the consumer crashes after writing to the DB but before committing the offset, so it reprocesses on restart. Fix: commit offsets after a successful write and make the DB write an upsert keyed by a business id.

**Q110. Kafka vs RabbitMQ? (Walmart signature)**
Kafka is a distributed log built for high-throughput streaming and replay — consumers track their own offset and data is retained. RabbitMQ is a traditional message broker (smart broker, push, per-message ack, complex routing) better for task queues and request/reply. Use Kafka for event streaming/analytics, RabbitMQ for classic queueing.

**Q111. What is log compaction?**
Compaction keeps at least the latest value per key in a topic, discarding older values. Great for changelog/state topics (e.g. current user profile) where you only care about the newest state.

**Q112. What happens when a consumer crashes?**
On restart it reads its last committed offset and resumes from there (at-least-once means it may reprocess a few). If it was in a group, the coordinator rebalances its partitions to the surviving consumers so processing continues.

---

## SECTION 8 — JPA & HIBERNATE (Q113–Q126)

**Q113. JPA vs Hibernate?**
JPA is the specification (interfaces, annotations) for ORM in Java; Hibernate is the most popular implementation of it. You code to JPA (`EntityManager`, annotations) and Hibernate does the work. Spring Data JPA sits on top to remove repository boilerplate.

**Q114. Explain the entity lifecycle states.**
Transient (new, not associated with a session), Persistent/Managed (attached, changes auto-tracked and flushed), Detached (was managed, session closed), Removed (marked for deletion). The `EntityManager`/Session moves entities between states.

**Q115. Lazy vs eager loading?**
Lazy loads associations only when accessed (default for collections) — efficient but can throw `LazyInitializationException` if the session is closed. Eager loads them immediately — convenient but can over-fetch. Best practice: keep things lazy and fetch what you need explicitly with a fetch join.

**Q116. Explain the N+1 problem and ALL the fixes. (most-asked Hibernate question)**
N+1: loading N parents lazily then triggering one query per parent's collection = 1 + N queries. Fixes: (1) `JOIN FETCH` in JPQL to load in one query; (2) `@EntityGraph` to declare what to fetch eagerly per query; (3) `@BatchSize` / `hibernate.default_batch_fetch_size` to load children in batches (turns N+1 into N/K+1); (4) a projection/DTO query selecting only needed columns. Always check the generated SQL with `show_sql`.

**Q117. Explain the caching levels.**
L1 (first-level) cache is the Session/`EntityManager` — on by default, scoped to one transaction, dedupes loads within it. L2 (second-level) cache is shared across sessions (Ehcache/Hazelcast/Redis) for read-mostly data. Query cache stores query result IDs. L2 isn't a silver bullet — it helps read-heavy, rarely-changing data and hurts write-heavy data.

**Q118. Optimistic vs pessimistic locking?**
Optimistic: add a `@Version` column; Hibernate checks it at flush and throws `OptimisticLockException` if another transaction changed the row — no DB locks, scales well, best when conflicts are rare. Pessimistic: take a DB row lock (`PESSIMISTIC_WRITE`) so others wait — guarantees exclusive access but reduces throughput and risks deadlocks; use for short, high-contention updates like account balances.

**Q119. persist vs merge vs save?**
`persist` (JPA) makes a new transient entity managed, returns void. `save` (Hibernate) does similar and returns the id. `merge` copies the state of a detached entity into a managed one and returns the managed instance — use it for updates to detached objects. Don't keep using the object you passed to `merge`; use the returned one.

**Q120. How do you write custom queries?**
JPQL/HQL with `@Query`, native SQL with `@Query(nativeQuery=true)`, derived query methods (`findByEmailAndStatus`), or the Criteria API for dynamic queries. Use projections/DTOs to fetch only needed fields.

**Q121. How do you do pagination?**
Pass a `Pageable` (`PageRequest.of(page, size, sort)`) to a Spring Data repository; it returns a `Page` with content and total count. Under the hood it adds LIMIT/OFFSET. For very large/deep pages, keyset (cursor) pagination performs better than offset.

**Q122. SessionFactory vs Session / EntityManagerFactory vs EntityManager?**
The factory is a heavyweight, thread-safe, create-once object holding config and the L2 cache. The Session/EntityManager is lightweight, single-threaded, short-lived — one unit of work per request, holding the L1 cache.

**Q123. Scenario: why are my auto-generated IDs not sequential (gaps)?**
With sequence/`AUTO` strategy, Hibernate pre-allocates ids in batches (default allocationSize 50) for performance, so restarts and rollbacks leave gaps. That's expected; if you need gapless ids use `IDENTITY` (DB auto-increment), accepting it disables JDBC batch inserts.

**Q124. How do you implement soft delete?**
Add an `is_deleted` flag and use `@SQLDelete` to turn DELETE into an UPDATE plus `@Where(clause = "is_deleted = false")` so queries auto-exclude deleted rows. Keeps history without physically removing data.

**Q125. What is the dirty checking mechanism?**
Within a transaction, Hibernate snapshots loaded entities and on flush/commit compares current state to the snapshot, auto-issuing UPDATEs for changed fields — you don't call save for managed entities.

**Q126. How do you fix Hibernate performance issues generally?**
Fix N+1 (fetch joins/batch size), select only needed columns (DTOs), enable JDBC batching for bulk writes, tune the connection pool (HikariCP), add the right DB indexes, use L2 cache for read-mostly data, and always inspect the actual SQL.

---

## SECTION 9 — SQL & DATABASES (Q127–Q140)

**Q127. Explain the JOIN types.**
INNER returns matching rows in both tables. LEFT returns all left rows + matches (nulls otherwise). RIGHT is the mirror. FULL returns all from both. CROSS is the Cartesian product. Most queries use INNER and LEFT.

**Q128. Find the second highest salary. (Cognizant/Accenture signature)**
Cleanest with a window function: `SELECT DISTINCT salary FROM (SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) rnk FROM employee) t WHERE rnk = 2;`. Simple version: `SELECT MAX(salary) FROM employee WHERE salary < (SELECT MAX(salary) FROM employee);`. DENSE_RANK generalizes to Nth and handles ties correctly.

**Q129. ROW_NUMBER vs RANK vs DENSE_RANK?**
For values 100,100,90: ROW_NUMBER gives 1,2,3 (always unique); RANK gives 1,1,3 (skips after ties); DENSE_RANK gives 1,1,2 (no gaps). Use DENSE_RANK for "top N distinct values," ROW_NUMBER to dedupe rows.

**Q130. Highest salary per department. (Accenture signature)**
`WITH r AS (SELECT name, dept, salary, DENSE_RANK() OVER (PARTITION BY dept ORDER BY salary DESC) rk FROM emp) SELECT * FROM r WHERE rk = 1;`. PARTITION BY restarts the ranking per department.

**Q131. GROUP BY vs HAVING vs WHERE?**
WHERE filters rows before grouping; GROUP BY aggregates; HAVING filters the aggregated groups. Example: `... WHERE active=1 GROUP BY dept HAVING COUNT(*) > 5`.

**Q132. What is an index and when does it hurt?**
An index is a sorted lookup structure (usually B-tree) that speeds reads by avoiding full scans — like a book index. Trade-off: it slows writes (must be maintained) and uses storage. Index columns used in WHERE/JOIN/ORDER BY; don't over-index write-heavy tables. Clustered index defines physical row order (one per table); non-clustered points to rows.

**Q133. Explain ACID.**
Atomicity (all or nothing), Consistency (valid state to valid state), Isolation (concurrent txns don't corrupt each other), Durability (committed data survives crashes). It's what makes relational DBs reliable for money/orders.

**Q134. What is normalization and when do you denormalize?**
Normalization removes redundancy by splitting data into related tables (1NF→3NF) — fewer anomalies. Denormalization deliberately duplicates data to speed reads (reporting/analytics). OLTP favors normalized; OLAP/reporting favors denormalized.

**Q135. UNION vs UNION ALL?**
UNION combines result sets and removes duplicates (extra sort/dedupe cost). UNION ALL keeps duplicates and is faster. Use UNION ALL unless you actually need dedupe.

**Q136. OLTP vs OLAP (e.g. MySQL vs Snowflake)?**
OLTP = many small, fast transactions (MySQL/Postgres) for app workloads. OLAP = large analytical scans over huge data (Snowflake/BigQuery), columnar storage. You move data from OLTP to OLAP for analytics.

**Q137. SQL vs NoSQL — how do you choose?**
SQL: structured data, strong consistency, complex joins/transactions (banking, orders). NoSQL: flexible schema, massive scale, high write throughput, simple access patterns (catalogs, sessions, event data). Choose by consistency needs, query shape, and scale; many systems use both.

**Q138. Explain transaction isolation anomalies.**
Dirty read (reading uncommitted data), non-repeatable read (same query returns different rows mid-txn), phantom read (new rows appear). Higher isolation levels prevent more anomalies at the cost of concurrency.

**Q139. How do you optimize a slow query?**
Run EXPLAIN/EXPLAIN ANALYZE to see the plan; look for full scans, missing indexes, expensive sorts. Add/adjust indexes, select only needed columns, avoid functions on indexed columns in WHERE, rewrite correlated subqueries as joins, and paginate. Test on production-like data.

**Q140. DROP vs DELETE vs TRUNCATE? (Cognizant signature)**
DELETE removes rows (can use WHERE), is logged row-by-row, and can be rolled back. TRUNCATE removes all rows fast, minimal logging, resets identity, usually can't be filtered. DROP removes the whole table/structure. DELETE is DML; TRUNCATE/DROP are DDL.

---

## SECTION 10 — MICROSERVICES ARCHITECTURE (Q141–Q154)

**Q141. What communication patterns do microservices use?**
Synchronous (REST/gRPC via Feign/WebClient) for request/response, and asynchronous (Kafka/RabbitMQ events) for decoupling and resilience. Async improves fault tolerance because services don't block on each other. Use sync for queries needing an immediate answer, async for state propagation.

**Q142. What is an API gateway?**
A single entry point that routes requests to services and handles cross-cutting concerns — auth/token validation, rate limiting, routing, SSL, aggregation. Spring Cloud Gateway is common. Keeps clients decoupled from internal topology.

**Q143. What is service discovery?**
A registry (Eureka/Consul) where services register and look each other up by name instead of hardcoded IPs — essential in dynamic/cloud setups where instances come and go. The gateway/clients query it to find healthy instances.

**Q144. Explain the circuit breaker pattern (Resilience4j). (high-signal)**
If a downstream service keeps failing, the circuit "opens" and calls fail fast (with a fallback) instead of piling up and cascading. After a cooldown it goes half-open to test recovery. Resilience4j provides this plus retry, rate limiter, and bulkhead. Example: recommendations service down → show trending products instead.

**Q145. Explain the Saga pattern. (deal-breaker question)**
For a business transaction spanning services, a Saga splits it into local transactions; if a step fails, it runs compensating actions to undo previous steps — it does NOT do a global rollback, it compensates. Two styles: choreography (services react to events) and orchestration (a coordinator drives steps). Use it for order→payment→inventory flows.

**Q146. How do you handle distributed transactions without 2PC?**
Avoid distributed locks/2PC (they don't scale). Use Saga for the workflow plus eventual consistency, and the outbox pattern to publish events reliably. Accept temporary inconsistency with guaranteed eventual correctness.

**Q147. Explain the outbox pattern.**
Problem: you must update your DB AND publish an event atomically, but they're two systems (dual-write risk). Solution: in the same DB transaction, write the business row AND an "outbox" row; a separate process (or Debezium CDC) reads the outbox and publishes to Kafka. Guarantees the event is sent if and only if the data was committed.

**Q148. What is eventual consistency?**
In distributed systems, data isn't consistent everywhere instantly; it converges after events propagate. You design for it (idempotent handlers, compensations) and set business expectations. Trade-off vs strong consistency, which costs latency/availability.

**Q149. What is distributed tracing and why do you need it?**
A request crosses many services, so you propagate a trace/correlation id (Micrometer Tracing / Sleuth + Zipkin/Jaeger) to follow it end-to-end and find where latency/errors occur. Essential for debugging microservices.

**Q150. Database-per-service — why and what's the catch?**
Each service owns its database so services stay loosely coupled and independently deployable. Catch: no cross-service joins or shared transactions — you handle cross-service data via APIs/events and eventual consistency (Saga/outbox).

**Q151. Scenario: a service fails intermittently. How do you make the system resilient?**
Add retries with backoff for transient failures, a circuit breaker to fail fast on repeated failures, timeouts so callers don't hang, a bulkhead to isolate the failure, and a fallback for graceful degradation. Add tracing/metrics/alerting to find the root cause, and idempotent handlers so retries are safe.

**Q152. How do you achieve zero-downtime deployment?**
Rolling updates or blue-green/canary deployments behind a load balancer, with Kubernetes readiness probes so traffic only hits ready pods, and backward-compatible API/DB changes. Roll back fast if health degrades.

**Q153. Monolith vs microservices — when do you NOT use microservices?**
Microservices add operational complexity (deployment, networking, observability, data consistency). For a small team or early product, a well-structured monolith is faster and cheaper. Split into services when you need independent scaling/deployment and clear domain boundaries. (Walmart commonly opens with "why microservices, not a monolith?")

**Q154. How do you monitor microservices?**
Metrics (Micrometer → Prometheus → Grafana), centralized logs (ELK/Loki) with correlation ids, distributed tracing (Zipkin/Jaeger), and health checks via Actuator. Alert on golden signals: latency, errors, traffic, saturation.

---

## SECTION 11 — REST API DESIGN (Q155–Q162)

**Q155. What makes an API RESTful?**
Resources as nouns (`/orders`), HTTP methods as actions, statelessness (each request self-contained), a uniform interface, and correct status codes. Anti-pattern: verbs in URLs like `/createOrder`.

**Q156. Map HTTP methods and idempotency.**
GET (read, safe+idempotent), POST (create, not idempotent), PUT (full replace, idempotent), PATCH (partial update, not necessarily idempotent), DELETE (remove, idempotent). Idempotency means repeating the call leaves the same state — critical for safe retries.

**Q157. PUT vs PATCH? (common)**
PUT replaces the entire resource (send the full object); PATCH updates only specified fields. PUT is idempotent; PATCH may or may not be depending on implementation ("set" is idempotent, "increment/append" isn't).

**Q158. How do you make POST safe to retry (idempotency keys)?**
The client sends a unique `Idempotency-Key` header; the server stores the result against that key and returns it on a retry instead of processing again — preventing double charges. Stripe, for example, *recommends* adding an idempotency key to all POST requests, saves the status code and body of the first request for any given key, returns the same stored result (including 500s) on subsequent calls with that key, and expires keys after 24 hours; V4 UUIDs are recommended as keys. Implement it with Redis (with a TTL) or a dedup table.

**Q159. Common status codes?**
200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable Entity, 429 Too Many Requests, 500 Internal Server Error. Use them precisely.

**Q160. How do you version an API?**
URI versioning (`/v1/orders`) — explicit, cache-friendly, easiest to route (most common); header/media-type versioning — cleaner URLs but harder to test. Whatever you pick, keep changes backward-compatible (add optional fields, never remove) and announce deprecations.

**Q161. Offset vs cursor pagination?**
Offset (`?offset=20&limit=10`) is simple but slow on deep pages and unstable under inserts. Cursor/keyset (`?after=<id>&limit=10`) uses an index seek — fast at any depth and stable. Use cursor pagination for large/real-time datasets (GitHub, Stripe, Slack do).

**Q162. How do you do validation and rate limiting?**
Validate with Bean Validation (`@Valid`, `@NotNull`, `@Size`) and return 400/422 with field-level errors via `@RestControllerAdvice`. Rate limit at the gateway or with Resilience4j RateLimiter, returning 429 when exceeded — protects against abuse and cost overruns.

---

## SECTION 12 — DOCKER (Q163–Q170)

**Q163. Containers vs VMs?**
VMs virtualize hardware and each runs a full OS — heavy, slow to start. Containers share the host kernel and isolate at the process level — lightweight, fast, dense. Containers are ideal for microservices.

**Q164. Image vs container?**
An image is the immutable blueprint (layers: base OS, deps, app). A container is a running instance of an image. One image → many containers.

**Q165. Write a multi-stage Dockerfile for Spring Boot and explain why. (common scenario)**
Stage 1 uses a JDK+Maven image to build the jar; stage 2 uses a slim JRE (or distroless) image and copies only the jar. This drops image size dramatically (commonly reported from ~880MB single-stage to ~400MB or less) and shrinks the attack surface because build tools aren't in the final image. Bonus: copy Maven deps before source so Docker layer caching speeds rebuilds.

**Q166. How do you optimize image size?**
Multi-stage builds, slim/alpine/distroless base images, JRE not JDK at runtime, combine RUN steps and clean caches in the same layer, use `.dockerignore`, and leverage Spring Boot layered jars so changing code doesn't invalidate dependency layers.

**Q167. What is docker-compose?**
A YAML file to define and run multi-container apps (app + DB + Kafka) on one network with one command — great for local dev and integration testing.

**Q168. What are volumes?**
Volumes persist data outside the container's writable layer so it survives restarts/recreations (e.g. DB data). Without them, container data is lost on removal. Bind mounts map host directories; named volumes are Docker-managed.

**Q169. How does Docker networking work?**
Containers on the same user-defined bridge network reach each other by service name. Compose creates this automatically. You publish ports (`-p 8080:8080`) to expose to the host.

**Q170. Scenario: how do you handle a container that keeps crashing?**
Check `docker logs`, fix the root cause (bad config/env, missing dependency), add a HEALTHCHECK and a restart policy, and set resource limits. In orchestration this maps to liveness/readiness probes.

---

## SECTION 13 — KUBERNETES (Q171–Q180)

**Q171. Explain pods, deployments, and services.**
A Pod is the smallest unit — one or more containers sharing network/storage. A Deployment manages replica Pods, rollouts, and self-healing. A Service gives a stable network endpoint/load-balancing to a set of Pods (whose IPs change).

**Q172. What is an Ingress?**
Ingress routes external HTTP(S) traffic to services based on host/path rules, with one entry point and TLS termination — instead of exposing many LoadBalancer services.

**Q173. ConfigMaps vs Secrets?**
ConfigMaps hold non-sensitive config; Secrets hold sensitive data (passwords, tokens), base64-encoded and mountable as env vars or files. Both decouple config from the image.

**Q174. Explain liveness, readiness, and startup probes and how they map to Spring Boot. (high-signal)**
Readiness = "can I serve traffic?" — failing removes the Pod from the Service (no restart). Liveness = "am I alive?" — failing restarts the container. Startup = "have I finished booting?" — gives slow apps time before liveness kicks in. With Spring Boot Actuator they map to `/actuator/health/readiness` and `/actuator/health/liveness`. Tune `initialDelaySeconds` so a slow JVM start doesn't trigger false restarts.

**Q175. Scenario: a pod is in CrashLoopBackOff with no useful logs. How do you debug? (very common)**
Get the previous container's logs (`kubectl logs <pod> --previous`) and events (`kubectl describe pod`) — check the exit code. Common causes: bad env/config, missing dependency (DB/Redis unreachable), failing migrations, or an aggressive liveness probe killing a slow-starting app. Temporarily override the command to keep it alive and inspect, then fix the probe timing or the config.

**Q176. How does HPA scaling work?**
The Horizontal Pod Autoscaler adds/removes pod replicas based on metrics (CPU/memory or custom). You set target utilization and min/max replicas. Pair with resource requests so scaling decisions are accurate.

**Q177. How do rolling updates and rollbacks work?**
Rolling update replaces pods gradually (`maxSurge`/`maxUnavailable`) so there's no downtime, gated by readiness probes. If something breaks, `kubectl rollout undo` reverts to the previous ReplicaSet. Use `maxUnavailable: 0` for safest zero-downtime.

**Q178. What are resource requests and limits?**
Requests = guaranteed resources used for scheduling; limits = the cap. Exceeding a memory limit gets the container OOM-killed; CPU over-limit is throttled. Set both to protect the node and get predictable scheduling.

**Q179. Scenario: a pod is Pending. Why?**
Usually no node has enough CPU/memory to satisfy its requests, an unbound PersistentVolumeClaim, node taints without tolerations, or affinity rules that can't be met. Check `kubectl describe pod` events and node capacity.

**Q180. How do you do zero-downtime deploys in Kubernetes?**
Rolling update with readiness probes + `maxUnavailable: 0`, a `preStop` hook and graceful shutdown so in-flight requests finish, and backward-compatible changes. Blue-green/canary for higher safety.

---

## SECTION 14 — GCP (Q181–Q188)

**Q181. What are the core GCP compute options for a Spring Boot app?**
Compute Engine (IaaS VMs — full control), GKE (managed Kubernetes — microservices at scale), Cloud Run (serverless containers — simplest, autoscales to zero), App Engine (PaaS). For a containerized stateless Spring Boot service I'd default to Cloud Run; for complex orchestration, GKE.

**Q182. Cloud Run vs GKE — how do you choose?**
Cloud Run: fully managed, serverless, scales to zero, no infra to run — best for stateless containers and spiky traffic. GKE: full Kubernetes control, custom networking, sidecars, stateful workloads. Pick Cloud Run for simplicity, GKE for control.

**Q183. What is Cloud SQL?**
A managed relational DB (MySQL/Postgres/SQL Server) with automated backups, replication, and patching. Connect from Cloud Run/GKE via the Cloud SQL connector or a private IP (Serverless VPC connector).

**Q184. Pub/Sub vs Kafka?**
Pub/Sub is GCP's fully managed messaging — no brokers to run, autoscaling, push/pull subscriptions, great for event-driven and decoupling. Kafka gives ordered partitioned logs, replay, and ecosystem (Streams/Connect) but you manage it (or use a managed Kafka). Choose Pub/Sub for managed simplicity, Kafka for streaming/ordering/replay.

**Q185. What is Cloud Storage and BigQuery?**
Cloud Storage = scalable object storage for files/backups/static content (storage classes for cost). BigQuery = serverless analytics data warehouse for fast SQL over huge datasets — the OLAP side.

**Q186. How do you manage secrets and identity securely on GCP?**
Use Secret Manager for credentials (don't bake them into images), and Workload Identity so GKE/Cloud Run workloads assume an IAM service account without storing key files — short-lived tokens, easy rotation. IAM enforces least privilege.

**Q187. How do you observe apps on GCP?**
Cloud Logging (centralized logs) and Cloud Monitoring (metrics, dashboards, alerting), formerly Stackdriver. Spring Boot integrates via Micrometer; alerts fire when thresholds are crossed.

**Q188. How would you deploy a Spring Boot service on Cloud Run?**
Containerize with a multi-stage Dockerfile, push to Artifact Registry, `gcloud run deploy` with the image, set env/secrets from Secret Manager, connect to Cloud SQL via the connector, and let Cloud Run autoscale on request volume.

---

## SECTION 15 — SYSTEM DESIGN (Q189–Q196)

**Q189. What framework do you use to answer a system design question?**
(1) Clarify functional + non-functional requirements and scale; (2) back-of-envelope estimates (QPS, storage); (3) define API + data model; (4) high-level architecture (boxes/arrows); (5) deep-dive 2–3 components; (6) discuss bottlenecks, scaling, failure modes, trade-offs. Always state assumptions out loud.

**Q190. Design a URL shortener. (Paytm/JPMorgan-style)**
Requirements: shorten, redirect, read-heavy (a common interview assumption is ~100M new URLs/day with a ~10:1 read:write ratio). API: `POST /urls`, `GET /{code}`. Generate a unique id (counter/Snowflake) and Base62-encode it — a 7-char Base62 string covers ~3.5 trillion (62^7) combinations — or hash+collision-check. Store `code→longURL` in a key-value/NoSQL store; cache hot mappings in Redis; use a 301 or 302 redirect. Scale: stateless web tier behind a load balancer, DB sharding/replication, rate limiting to prevent abuse. Trade-off: 301 (cacheable, less load) vs 302 (enables click analytics because requests keep hitting your service).

**Q191. Design a rate limiter. (Walmart LLD-style)**
Requirements: limit N requests per user/IP per window. Algorithms: fixed window (simple, boundary bursts), sliding window (smoother), token bucket (allows bursts, common), leaky bucket (smooths output). Store counters in Redis (atomic INCR with TTL, or token bucket via a Lua script) for a distributed limiter shared across instances; return 429 with `Retry-After`. Place it at the API gateway. Trade-off: accuracy vs memory/latency.

**Q192. Design a notification service.**
Requirements: send email/SMS/push across millions of users, reliably. Producers publish notification events to Kafka/Pub/Sub; channel-specific consumers (email, SMS, push) process them; use templates, user preferences, and rate limits per provider. Make it async and idempotent, with retries + DLQ for failures, and a dedupe key so users aren't notified twice. Scale by partitioning per channel/user.

**Q193. Design a chat system.**
Requirements: 1:1 + group, online presence, delivery. Use WebSocket connections via a gateway, a message service writing to a fast store (Cassandra keyed by conversation), a fan-out via a message queue, and presence tracked in Redis. Guarantee ordering per conversation (sequence ids), at-least-once delivery with client dedupe, and offline storage + push notifications. Scale connections with sticky sessions/consistent hashing.

**Q194. Design an e-commerce order system.**
Services: Order, Payment, Inventory, Notification — database-per-service. Place order → Saga coordinates payment + inventory reservation; on failure, compensate (release inventory, refund). Use the outbox pattern for reliable events, idempotency keys for payments, and eventual consistency. Cache catalog reads; use a durable queue for order events. Trade-off: strong consistency on payment vs eventual on inventory views.

**Q195. How do you scale a system to millions of users?**
Stateless services behind load balancers (scale horizontally), caching (Redis/CDN) for read-heavy paths, DB read replicas + sharding for writes, async processing via queues, and event-driven decoupling. Add observability and autoscaling. Identify the bottleneck first — don't optimize blindly.

**Q196. Explain CAP theorem and caching strategies.**
CAP: under a network partition you choose Consistency or Availability (you can't have both); CP systems reject some requests to stay consistent, AP systems stay up but may be stale. Caching: cache-aside (app loads on miss — most common), write-through (write cache+DB together), write-behind (async write). Always set TTLs and plan invalidation; watch for thundering herd and stale data.

---

## SECTION 16 — LOW-LEVEL DESIGN / OOD & DESIGN PATTERNS (Q197–Q206)

**Q197. Design a parking lot (LLD).**
Entities: `ParkingLot`, `Level`, `ParkingSpot` (with sizes: small/medium/large), `Vehicle` (Car/Bike/Truck), `Ticket`. Behaviors: park (find nearest fit spot), unpark, calculate fee. Use Strategy for pricing, Factory for vehicle/spot creation, and an interface for spot-finding. Keep it extensible (new vehicle types, pricing rules) and thread-safe for concurrent entries.

**Q198. Design a payment system (LLD).**
Core: `PaymentService` with a `PaymentGateway` interface and implementations (Card, UPI, Wallet) — Strategy pattern. Use idempotency keys to avoid double charges, a state machine for payment status (INITIATED→AUTHORIZED→CAPTURED/FAILED), retries with backoff, and an outbox for events. Encrypt sensitive data; never log card numbers.

**Q199. Razorpay-style: design an in-memory database (LLD coding).**
Model `Database` → `Table` → rows with a defined schema (primary key, varchar length constraints). Methods: `createDatabase`, `createTable`, `insert` (validate PK uniqueness + constraints), `delete`, `search`, `deleteTable`. Use OOP: classes for Column/Constraint, a Map keyed by primary key for O(1) lookup, and throw clear exceptions on constraint violations. Discuss approach first, then write working code.

**Q200. Implement a thread-safe Singleton.**
Best: an enum (`enum Config { INSTANCE; }`) — JVM guarantees one instance and handles serialization. Otherwise use double-checked locking with a `volatile` instance: check null, synchronize, check again, create. Or the static holder idiom (`Holder.INSTANCE`) which is lazy and thread-safe via class loading.

**Q201. Factory pattern — what and why?**
A Factory centralizes object creation behind a method so callers don't use `new` directly — easy to add new types and swap implementations. Example: a `PaymentFactory.create(type)` returns the right gateway. Spring's `BeanFactory` is a factory.

**Q202. Builder pattern — when do you use it?**
For objects with many optional fields, Builder gives readable, immutable construction: `User.builder().name(..).email(..).build()`. Avoids telescoping constructors. Lombok's `@Builder` generates it.

**Q203. Strategy pattern?**
Encapsulate interchangeable algorithms behind an interface and pick one at runtime. Example: different `DiscountStrategy` or `PaymentStrategy`. Removes big if/else chains and is open for extension.

**Q204. Observer pattern?**
Subjects notify registered observers of changes (publish/subscribe in-process). Example: an order event notifies email + inventory listeners. Spring's `ApplicationEventPublisher` is this pattern.

**Q205. Which design patterns does Spring use?**
Singleton (beans by default), Factory (BeanFactory/ApplicationContext), Proxy (AOP, @Transactional), Template method (JdbcTemplate, RestTemplate), Observer (application events), Dependency Injection, and Decorator. Mentioning these shows you understand the framework, not just use it.

**Q206. Composition over inheritance — why?**
Inheritance is rigid (tight coupling, fragile base class). Composition (has-a) is flexible — you swap behavior at runtime and avoid deep hierarchies. Favor it; use inheritance only for true is-a relationships.

---

## SECTION 17 — DSA / CODING PROBLEMS (Q207–Q231)

For each: approach + complexity. State your plan and edge cases before coding.

**Q207. Two Sum.** Use a HashMap of value→index; for each number check if `target - num` exists. O(n) time, O(n) space — beats the O(n²) brute force.

**Q208. Find the second largest element.** One pass tracking `largest` and `secondLargest`, updating carefully on ties. O(n) time, O(1) space.

**Q209. Group Anagrams.** Key a HashMap by the sorted characters (or a 26-count signature) of each word; group words under the same key. O(n·k log k) time.

**Q210. Longest substring without repeating characters.** Sliding window with a Set/Map of last-seen index; move the left pointer past duplicates. O(n) time.

**Q211. Implement an LRU Cache.** Use a HashMap + doubly linked list (or Java's `LinkedHashMap` with access order). get/put move/insert the node to the front; evict from the tail when over capacity. O(1) per operation.

**Q212. Valid Parentheses.** Push opening brackets on a stack; on a closing bracket, the top must match. Valid if the stack ends empty. O(n) time.

**Q213. Reverse a linked list.** Iterate with three pointers (prev, curr, next), flipping each `next` to `prev`. O(n) time, O(1) space.

**Q214. Detect a cycle in a linked list.** Floyd's slow/fast pointers; if they meet there's a cycle. O(n) time, O(1) space.

**Q215. Binary tree level-order traversal.** BFS with a queue, processing level by level. O(n) time.

**Q216. Number of Islands.** Grid DFS/BFS: for each unvisited land cell, flood-fill its connected land and count. O(rows·cols).

**Q217. Course Schedule (cycle detection in a graph).** Topological sort via Kahn's algorithm (BFS on in-degrees) or DFS coloring; if you can't process all nodes there's a cycle. O(V+E).

**Q218. Climbing Stairs.** DP: ways(n) = ways(n-1) + ways(n-2) — it's Fibonacci. O(n) time, O(1) space.

**Q219. Coin Change (min coins).** DP array where `dp[amt] = min(dp[amt - coin] + 1)`. O(amount·coins) time.

**Q220. Subarray Sum Equals K.** Prefix sum + HashMap of seen sums; for each running sum check if `sum - k` was seen. O(n) time.

**Q221. Trapping Rain Water.** Two pointers tracking leftMax/rightMax; water at each index = min(maxes) − height. O(n) time, O(1) space.

**Q222. Check palindrome (string/number).** Two pointers from both ends comparing characters. O(n) time, O(1) space.

**Q223. Find duplicates in an array. (Accenture/JPMorgan signature)** Use a HashSet — if add() returns false it's a duplicate; or for values 1..n use index marking for O(1) space. O(n) time.

**Q224. Character/element frequency count.** Build a HashMap (or int[26]) of counts in one pass. O(n) time.

**Q225. Merge Intervals.** Sort by start, then merge overlapping intervals into the previous one. O(n log n) time.

**Q226. Kth largest element.** Maintain a min-heap of size k; the root is the answer. O(n log k) time. (Or QuickSelect O(n) average.)

**Q227. Maximum Subarray (Kadane's).** Track running sum, reset to current element when it goes negative, keep the max seen. O(n) time.

**Q228. Product of array except self.** Prefix and suffix products without division: two passes. O(n) time, O(1) extra (besides output).

**Q229. Delete a node given only its pointer (no head). (Paytm/Razorpay signature)** Copy the next node's value into this node and bypass the next node (`node.val = node.next.val; node.next = node.next.next`). O(1) — works because you can't reach the previous node.

**Q230. Maximum product leaving exactly one element out. (Walmart signature)** Compute prefix and suffix products; for each index the product is `prefix[i-1] * suffix[i+1]`; take the max. O(n) time. Handle zeros/negatives carefully.

**Q231. Implement a stack/queue from scratch or sort objects with Streams.** Stack via array/linked list with push/pop/peek; queue via two stacks or a circular buffer. Sorting objects: `list.sort(Comparator.comparing(...))` — know both the manual and Stream approaches.

---

## SECTION 18 — BEHAVIORAL / HR / MANAGERIAL (Q232–Q245)

Use the STAR method (Situation, Task, Action, Result) and add a Reflection (what you learned). Prepare 3–5 strong stories you can flex across questions.

**Q232. Tell me about yourself.** Use Present-Past-Future in ~60–90 seconds: current role and key responsibilities (e.g. "I'm a Java backend engineer at Cognizant building Spring Boot microservices with Kafka and SQL"), a relevant past achievement with a metric, then why this role is the logical next step. Keep it relevant to the job, not your life story.

**Q233. Why are you switching / leaving Cognizant?** Stay positive — frame it as seeking growth, deeper technical ownership, modern stack, and scale, not running away. Example: "I've grown a lot in services delivery; now I want to own product features end-to-end at scale, which this role offers." Never bad-mouth the current employer.

**Q234. Tell me about a conflict with a teammate.** STAR: pick a real disagreement (e.g. design approach), show you listened, used data/a quick POC to decide objectively, and preserved the relationship. Result: a better outcome and a stronger working relationship. Emphasize empathy and influence, not "I won."

**Q235. Tell me about leadership / mentoring.** Describe mentoring a junior or leading a module: how you guided them, unblocked them, reviewed code, and the measurable result (faster onboarding, fewer bugs). Shows the seniority expected at 5 YOE.

**Q236. What are your strengths and weaknesses?** Strength: tie to the role with evidence ("strong at debugging production issues — I cut incident time on X"). Weakness: a genuine one plus active improvement ("I used to over-engineer; now I time-box design and seek early feedback"). Avoid fake weaknesses.

**Q237. Where do you see yourself in 5 years?** Show ambition aligned with the company: growing into a senior/lead engineer owning architecture and mentoring, deepening in distributed systems. Signals commitment and a growth mindset.

**Q238. Tell me about a time you failed / handled failure.** Pick a real failure, own it without blaming, explain what you fixed and the lasting change (e.g. added tests/monitoring after a production bug). The Reflection is the most important part — what you learned.

**Q239. Tell me about a challenging technical problem you solved.** STAR with specifics: the problem (e.g. high consumer lag / a slow API), your diagnosis, the fix (added batching/indexes/caching), and a quantified result ("latency dropped from 2s to 200ms, handled 5x traffic"). Numbers make it credible.

**Q240. How do you handle tight deadlines / pressure?** Show prioritization: break work down, set internal milestones, communicate risks early, and protect quality. Give a concrete example of delivering multiple things on time by prioritizing ruthlessly.

**Q241. Why should we hire you?** Connect your exact skills (Java, Spring Boot, Kafka, microservices, cloud) to their needs, plus a track record of delivery and learning quickly. Be specific and confident, not generic.

**Q242. Salary negotiation: you're at ~11 LPA and targeting 15–20. How do you handle it?** Don't anchor on your current CTC; anchor on the market rate for the role and your skills. A 35–50% switch hike is realistic (≈15–16.5 LPA), and 18–20 LPA is achievable with a services→product/GCC move plus a competing offer. Delay the number to later rounds, benchmark on AmbitionBox/Glassdoor/Levels, negotiate total CTC (base + joining bonus + variable + ESOPs), and use a short notice period as leverage (some reports suggest firms pay a premium to onboard within ~30 days). If pushed early: "Engineers with my experience and stack in this market are around X–Y; I'm confident we can land on a number that reflects the value I bring."

**Q243. How do you handle critical feedback / a disagreement with your manager?** Show maturity: listen, separate ego from the work, ask clarifying questions, and act on valid feedback. Give an example where feedback made your work better.

**Q244. What questions do you have for us? (always ask some)** Ask thoughtful ones: "What does success look like in 6 months?", "How is the team structured and how are decisions made?", "What's the tech stack and the biggest technical challenge right now?", "How do you handle on-call and deployments?" Shows genuine interest and helps you assess fit.

**Q245. Describe your day-to-day work. (Cognizant/Accenture opener)** Be practical: pick up stories in scrum, develop/review APIs, write SQL and unit tests, debug across microservices, raise PRs, deploy services, and do health checks. Shows you actually do the work, not just theory.

---

## RECOMMENDATIONS

**Staged 6–8 week prep plan:**
1. **Weeks 1–2 (Foundations):** Lock Core Java, Java 8 Streams (write them live daily), Collections internals (HashMap/ConcurrentHashMap), and concurrency. These appear in nearly every interview and are the fastest scoring areas.
2. **Weeks 2–4 (Framework + Data):** Spring Boot, @Transactional pitfalls, Spring Security/JWT, JPA/Hibernate N+1, and SQL window-function problems. Practice explaining out loud in simple language.
3. **Weeks 3–5 (Distributed + Cloud):** Kafka (consumer-lag and exactly-once scenarios), microservices patterns (Saga/outbox/circuit breaker), Docker/Kubernetes (CrashLoopBackOff, probes), and your GCP services.
4. **Weeks 4–6 (DSA + Design):** Solve the 25 problems above until automatic; do 2–3 system-design walkthroughs (URL shortener, rate limiter) and 1–2 LLD (parking lot, rate limiter) end-to-end on a whiteboard.
5. **Weeks 6–8 (Mock + Behavioral):** Prepare 5 STAR stories, rehearse salary negotiation, and do mock interviews under time pressure.

**Targeting strategy by company type:**
- **Services (Cognizant/Accenture/TCS/Infosys/Wipro):** typically 2 technical + HR; lighter coding, heavy Java 8/Spring Boot/SQL concepts. Highest hit-rate for quick offers but smaller hikes (commonly ~20–35%).
- **GCCs/Product/Fintech (JPMorgan/Walmart/Paytm/Razorpay/PayPal/Optum):** OA → 2–3 technical (DSA medium + system design/LLD) → behavioral. Bigger hikes (often 40%+) but invest more in DSA and design. **System design is expected at 5 YOE here.**

**Benchmarks that change your strategy:**
- If you can solve LeetCode-medium in <25 min and clear a system-design walkthrough confidently → prioritize product/GCC applications and aim for 18–20 LPA.
- If DSA is shaky → start with services firms (faster offers), then use one as a competing offer to negotiate up elsewhere.
- Always try to secure 2 offers before negotiating — a competing offer is the single most effective lever reported.

## CAVEATS
- Company-specific questions and round structures come from self-reported interview experiences (Medium, GeeksforGeeks, Glassdoor, LeetCode); they're directionally reliable through cross-corroboration but not officially verified, and individual loops vary by team and interviewer.
- Salary hike percentages (~20–50%) are from community forums and advisory guides, not formal compensation surveys — treat them as indicative ranges that depend on your skills, the company, and 2024–2026 market conditions.
- Java-version features (records 16, sealed classes 17, virtual threads/JEP 444 in 21) assume modern JDKs; confirm the target company's JDK version, as many enterprises still run Java 8/11.
- HashMap internals (TREEIFY_THRESHOLD 8, UNTREEIFY 6, MIN_TREEIFY_CAPACITY 64, load factor 0.75) are from the OpenJDK source and apply to the standard JDK; behavior in older Java 7 differs (no treeification).
- Interviewers value clear reasoning and trade-off awareness over memorized definitions — state your assumptions and think out loud rather than reciting these answers verbatim.
