using System;
using UnityEngine;
using UnityEngine.AI;

namespace OUAT.World
{
    /// <summary>크리처 하나. 자세·이동·따라오기(동행)·머리 위 말. 데이터 id는 chapter1.json의 npcs[].id.</summary>
    public class NpcActor : MonoBehaviour
    {
        public string npcId;
        public Transform headAnchor;
        public float walkSpeed = 2.2f;

        NavMeshAgent agent;
        ProceduralRig rig;
        Transform follow;
        float followDist = 1.6f;
        Action onArrive;
        Vector3? lookAt;

        public ProceduralRig Rig => rig;
        public bool Following => follow != null;
        public bool Leading => leadTarget.HasValue;
        public Vector3? LeadTarget => leadTarget;

        // ── 앞장서기(넛지): 목표 쪽으로 걷다가 주인공이 멀어지면 멈춰 돌아보고 손짓, 가까워지면 다시 걷는다 ──
        Vector3? leadTarget; Transform leadPlayer; Action leadArrive; bool leadWaiting; float beckonTimer;
        public float leadGap = 6.5f, leadResume = 4.2f, leadDone = 4.5f;

        public void Lead(Vector3 target, Transform player, Action arrive = null)
        {
            follow = null; onArrive = null;
            leadTarget = target; leadPlayer = player; leadArrive = arrive; leadWaiting = false; beckonTimer = 0.8f;
            if (agent && agent.isOnNavMesh && NavMesh.SamplePosition(target, out var hit, 3f, NavMesh.AllAreas)) { leadTarget = hit.position; agent.SetDestination(hit.position); }
        }
        public void StopLead() { leadTarget = null; leadArrive = null; }

        void UpdateLead()
        {
            if (!leadTarget.HasValue || !leadPlayer || agent == null || !agent.isOnNavMesh) return;
            float gap = Vector3.Distance(transform.position, leadPlayer.position);
            // 도착: 목적지 0.8m 안, 또는 목적지가 막힘 위라 더 못 가고 멈춘 경우(부분 경로 끝) — QA P0-5
            bool stuckAtEnd = !agent.pathPending && agent.hasPath == false && agent.velocity.sqrMagnitude < 0.01f && Vector3.Distance(transform.position, leadTarget.Value) < 3f;
            bool partialDone = !agent.pathPending && agent.pathStatus != NavMeshPathStatus.PathComplete && agent.remainingDistance < 0.3f;
            bool there = Vector3.Distance(transform.position, leadTarget.Value) < 0.8f || ((stuckAtEnd || partialDone) && !leadWaiting);
            if (there || gap > leadGap || (leadWaiting && gap > leadResume))
            {
                // 멈춰서 돌아보고, 가끔 손짓(이리 와)
                if (!leadWaiting) { leadWaiting = true; agent.ResetPath(); beckonTimer = 0.4f; }
                lookAt = leadPlayer.position;
                beckonTimer -= Time.deltaTime;
                if (beckonTimer <= 0f) { beckonTimer = 3.2f; Beckon(); }
                if (there && gap < leadDone && leadArrive != null) { var cb = leadArrive; StopLead(); lookAt = null; SetPose(ProceduralRig.Pose.Stand); cb?.Invoke(); }
                return;
            }
            if (leadWaiting) { leadWaiting = false; SetPose(ProceduralRig.Pose.Stand); agent.SetDestination(leadTarget.Value); }
            agent.speed = walkSpeed;
        }

        void Beckon()
        {
            if (!rig) return;
            rig.SetPose(ProceduralRig.Pose.Point);
            CancelInvoke(nameof(EndBeckon)); Invoke(nameof(EndBeckon), 1.1f);
        }
        void EndBeckon() { if (rig && leadWaiting) rig.SetPose(ProceduralRig.Pose.Stand); }
        public Vector3 HeadPosition => headAnchor ? headAnchor.position : transform.position + Vector3.up * HeightGuess();

        void Awake()
        {
            agent = GetComponent<NavMeshAgent>();
            rig = GetComponentInChildren<ProceduralRig>();
            if (agent) { agent.speed = walkSpeed; agent.acceleration = 12f; agent.angularSpeed = 540f; agent.stoppingDistance = 0.2f; }
        }

        float HeightGuess()
        {
            var b = new Bounds(transform.position, Vector3.zero);
            foreach (var r in GetComponentsInChildren<Renderer>()) b.Encapsulate(r.bounds);
            return Mathf.Max(1f, b.max.y - transform.position.y) + 0.25f;
        }

        public void SetPose(ProceduralRig.Pose p) { if (rig) rig.SetPose(p); }

        public void Follow(Transform t, float distance = 2.1f) { StopLead(); follow = t; followDist = distance; }
        public void StopFollow() { follow = null; if (agent && agent.isOnNavMesh) agent.ResetPath(); }

        public void WalkTo(Vector3 p, Action arrive = null, bool routed = false)
        {
            var areas = OUAT.Core.AreaSystem.I;
            if (!routed && areas != null && areas.isActiveAndEnabled && areas.Of(transform.position) != areas.Of(p))
            { follow = null; StopLead(); StartCoroutine(areas.Route(this, p, arrive)); return; }
            follow = null; StopLead(); onArrive = arrive;
            if (agent && agent.isOnNavMesh && NavMesh.SamplePosition(p, out var hit, 3f, NavMesh.AllAreas)) agent.SetDestination(hit.position);
            else { transform.position = p; arrive?.Invoke(); onArrive = null; }
        }

        public void Warp(Vector3 p) { if (agent && agent.isOnNavMesh) agent.Warp(p); else transform.position = p; }

        public void LookAt(Vector3? p) { lookAt = p; }

        void Update()
        {
            UpdateLead();
            if (agent && agent.isOnNavMesh)
            {
                if (follow)
                {
                    float d = Vector3.Distance(transform.position, follow.position);
                    // 주인공 바로 앞을 막지 않게 뒤쪽 비스듬한 자리로
                    var behind = follow.position - follow.forward * followDist * 0.8f + follow.right * 0.9f;
                    if (d > followDist + 0.4f) agent.SetDestination(behind);
                    else if (d < followDist * 0.8f) agent.ResetPath();
                    agent.speed = d > 5f ? walkSpeed * 1.8f : walkSpeed * 1.35f;
                }
                if (onArrive != null && !agent.pathPending && agent.remainingDistance <= agent.stoppingDistance + 0.1f)
                { var cb = onArrive; onArrive = null; cb(); }
                if (rig) rig.speed = agent.velocity.magnitude;
            }
            if (lookAt.HasValue && (agent == null || agent.velocity.sqrMagnitude < 0.05f))
            {
                var dir = lookAt.Value - transform.position; dir.y = 0;
                if (dir.sqrMagnitude > 0.01f) transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(dir), Time.deltaTime * 5f);
            }
        }
    }
}
