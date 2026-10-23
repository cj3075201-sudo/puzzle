using System;
using UnityEngine;
using UnityEngine.AI;

namespace OUAT.World
{
    /// <summary>마우스 클릭 이동(화-03). 땅을 누르면 그곳으로, 대상을 누르면 대상의 다가설 자리로 걸어간 뒤 알린다.</summary>
    [RequireComponent(typeof(NavMeshAgent))]
    public class PlayerMover : MonoBehaviour
    {
        public float walkSpeed = 1.8f;
        public float runSpeed = 3.2f;
        public LayerMask groundMask = ~0;
        public ClickMarker marker;

        NavMeshAgent agent;
        ProceduralRig rig;
        Action onArrive;
        Vector3 faceTarget;
        bool hasFace;

        public bool InputLocked { get; set; }
        public bool IsMoving => agent != null && agent.hasPath && agent.remainingDistance > agent.stoppingDistance + 0.05f;
        public NavMeshAgent Agent => agent;

        void Awake()
        {
            agent = GetComponent<NavMeshAgent>();
            agent.speed = walkSpeed;
            agent.acceleration = 18f;
            agent.angularSpeed = 720f;
            agent.stoppingDistance = 0.1f;
            agent.radius = 0.32f;
            agent.height = 1.1f;
            // 좁은 틈(굴 입구 0.9m)에서 앞장서 기다리는 키노피오에 막히지 않게 — 주인공은 크리처를 비켜 가지 않고 지나감(자동 완주 10/23)
            agent.obstacleAvoidanceType = ObstacleAvoidanceType.NoObstacleAvoidance;
            agent.avoidancePriority = 0;
            rig = GetComponentInChildren<ProceduralRig>();
        }

        public void Warp(Vector3 p) { agent.Warp(p); agent.ResetPath(); }

        public void WalkTo(Vector3 p, Action arrive = null, Vector3? face = null)
        {
            onArrive = arrive;
            hasFace = face.HasValue; if (hasFace) faceTarget = face.Value;
            if (NavMesh.SamplePosition(p, out var hit, 3f, NavMesh.AllAreas))
            {
                // 가까우면 걷고(1.8) 멀면 뛴다(3.2) — 사람 아이 걸음에 맞춘 속도(발 미끄럼 없음)
                agent.speed = Vector3.Distance(transform.position, hit.position) > 7f ? runSpeed : walkSpeed;
                agent.SetDestination(hit.position);
                if (marker && arrive == null) marker.Show(hit.position);
            }
            else onArrive?.Invoke();
        }

        public void Stop() { agent.ResetPath(); onArrive = null; }

        public void Face(Vector3 p) { faceTarget = p; hasFace = true; }

        float stepTimer;

        void Update()
        {
            if (rig) rig.speed = agent.velocity.magnitude;
            if (agent.velocity.magnitude > 0.6f)
            {
                stepTimer -= Time.deltaTime;
                if (stepTimer <= 0f) { stepTimer = 0.36f; OUAT.Core.AudioHub.PlayVariant("step_paper", 3, 0.25f); }
            }
            else stepTimer = 0.1f;

            if (onArrive != null && !agent.pathPending && agent.remainingDistance <= agent.stoppingDistance + 0.08f)
            {
                var cb = onArrive; onArrive = null;
                cb();
            }
            if (hasFace && !IsMoving)
            {
                var d = faceTarget - transform.position; d.y = 0;
                if (d.sqrMagnitude > 0.01f)
                    transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(d), Time.deltaTime * 8f);
            }
        }
    }
}
