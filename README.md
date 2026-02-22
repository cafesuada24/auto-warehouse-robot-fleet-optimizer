# Multi-Agent Task Allocation & Simulation Platform

## 1. Overview
This project implements a distributed, event-driven system for multi-robot task allocation and execution simulation. It is designed to support:
- Deterministic simulation and replay

- Pluggable allocation strategies

- Event sourcing for traceability

- Scalable multi-agent decision logic

- Future integration of learned models

The system is structured as loosely coupled services communicating via a message bus, enabling independent development, testing, and deployment.

## 2. System Architecture
### 2.1 High-level Components
| Component | Responsibility |
| --- | --- |
| Event Bus | Asynchronous pub/sub communication backbone |
| Simulator Service | Simulates robots, task execution, and world state |
| Allocator Service | Assigns tasks to robots based on policy |
| Event Store (JSONL) | Assigns tasks to robots based on policy |
| Replay Tool | Deterministic reconstruction of system state |

The architecture follows an event-driven, state-reduced design, where services react to events and emit new events.

## 3. Core Principles
### 3.1 Event-Driven Architecture
- All state transitions are triggered by events.
- Services do not directly invoke each other.
- The system supports deterministic replay.

### 3.2 Event Sourcing
- Events are stored in JSONL format.
- System state can be reconstructed from command streams.
- Replay enables:
    - Debugging
    - Deterministic testing
    - Offline evaluation of new allocation strategies

### 3.3 Determinism First
- timestamp used for ordering.
- UUID used only for identity, not ordering.
- Sequential event processing for now (multithreading deferred).

## 4. Simulator Service
### 4.1 Responsibilities
- Maintain robot state
- Execute tasks
- Publish robot state updates
- Accept or reject task assignments
- Provide reset capability for replay

### 4.2 Key Features Implemented
- Reset function for deterministic replay
- Assignment acceptance/rejection events
- Robot state publication
- Command handling

### 4.3 Event Types (Examples)
| Topic	| Description |
| --- | --- |
| ROBOT_STATE | Periodic robot state updates |
| TASK:ASSIGNMENT:COMMAND | Allocator assigns task |
| TASK:ASSIGNMENT:ACCEPTED | Simulator confirms assignment |
| TASK:ASSIGNMENT:REJECTED | Simulator rejects assignment 

## 5. Allocator Service 
### 5.1 Responsibilities
- Maintain robot and task views
- Track availability
- Allocate tasks in batches
- Handle acceptance and rejection
- Maintain assignment lifecycle integrity


### 5.3 Allocation Flow

## 6. Assignment Lifecycle

## 7. Event Store (JSONL)

Each line contains:
```json
{
  "event_id": "uuid",
  "timestamp_ms": 1700000000000,
  "topic": "TASK:ASSIGNMENT:COMMAND",
  "payload": { ... }
}
```

Purpose:
- Deterministic replay
- Audit trail
- Model training dataset generation
- Post-hoc performance evaluation

8. Multi-Agent AI
The allocator is the decision core. It can evolve from:
- Rule-based heuristic allocation
- Cost-based optimization
- To learned policy (RL / imitation learning)

Training Data Sources

From recorded events:
- Robot state
- Task features
- Assignment outcomes
- Acceptance/rejection
- Completion time
- Energy usage

This enables:
- Learning robot-task matching models
- Predicting acceptance probability
- Learning dispatch policies
- Simulation-based reinforcement learning

## 9. Current Implementation Status

### 9.1 Simulator
- Event-driven processing
- Reset for replay
- Assignment lifecycle handling
- Robot state updates

### 9.2 Allocator
- Batch allocation loop
- Accept/reject handling
- Late acceptance protection

## 10. Immediate Next Steps
### 10.1 Allocator
#### Reliability
- Backoff strategy for repeated rejections
- Assignment expiration timeout
- Idempotent event handling

#### Allocation Quality
- Replace FIFO re-queue with:
    - Cooldown policy
    - Robot-task compatibility scoring
- Add distance-based cost model
- Battery-aware filtering

#### Observability
- Allocation metrics:
    - Acceptance rate
    - Average allocation latency
    - Task wait time
    - Robot utilization
- Structured logging

#### Robustness
- Assignment timeout cleanup
- Duplicate event protection
- Invariant validation hooks
