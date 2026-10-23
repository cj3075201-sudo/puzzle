using System.Linq;
using OUAT.World;
using UnityEngine;

namespace OUAT.Core
{
    /// <summary>
    /// 길잡이 — 화면 글자(목표 쪽지·힌트 토스트) 없이 세계 안에서 다음 할 일로 이끈다(사용자 10/23 “본게임에서는 안쓸거거든 … 자연스럽게 행동을 유도하는 넛지”).
    /// 지금 목표(goals[], 화면에는 안 보임)의 target을 기준으로:
    /// ① 늘: 대상이 가까우면(7m) 은은하게 반짝임 — 색 있는 사람 물건·걸쇠가 눈에 걸리게
    /// ② 20초 진행 없음: 대상이 크게 반짝이고 작은 소리
    /// ③ 45초: 키노피오가 있으면 대상(또는 그쪽 출구) 쪽으로 몇 걸음 가서 가리키고 돌아봄
    /// ④ 90초: 주인공의 짧은 생각(goals[].thought) — 한 목표에 한 번
    /// 뜻은 알려 주지 않는다(뜻-07). 개발용 표식은 F2.
    /// </summary>
    public class GuideSystem : MonoBehaviour
    {
        public float glintAt = 20f, kidAt = 45f, thoughtAt = 90f;
        Transform marker;
        string lastGoal;
        float idle, nearGlint;
        int stage;
        int lastFlagCount;
        bool devMarker;

        Game G => Game.I;

        void Start()
        {
            marker = BuildMarker().transform;
            marker.gameObject.SetActive(false);
        }

        GameObject BuildMarker()
        {
            var go = new GameObject("GoalMarker(dev)");
            var mf = go.AddComponent<MeshFilter>();
            var mr = go.AddComponent<MeshRenderer>();
            var m = new Mesh();
            m.vertices = new[] { new Vector3(0, 0.45f, 0), new Vector3(0.28f, 0, 0), new Vector3(0, -0.45f, 0), new Vector3(-0.28f, 0, 0) };
            m.triangles = new[] { 0, 1, 2, 0, 2, 3, 0, 2, 1, 0, 3, 2 };
            m.RecalculateBounds();
            mf.sharedMesh = m;
            var ink = new Material(Shader.Find("OUAT/Unlit")); ink.SetColor("_BaseColor", new Color(0.9f, 0.2f, 0.2f, 1)); ink.SetFloat("_Cull", 0); ink.renderQueue = 3100;
            mr.sharedMaterial = ink;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return go;
        }

        string TargetId(GoalDef goal) => goal?.Raw != null ? J.Str(goal.Raw, "target") : null;

        /// <summary>목표 대상의 세계 위치(다른 구역이면 그쪽 출구).</summary>
        public Vector3? TargetPoint(out Transform follow, out bool viaExit)
        {
            follow = null; viaExit = false;
            var g = G;
            var id = TargetId(g.Data.CurrentGoal(g.State));
            if (string.IsNullOrEmpty(id)) return null;
            var n = g.Npc(id); var pz = g.Puzzle(id);
            if (n && !n.gameObject.activeInHierarchy) return null;
            Vector3 raw = n ? n.transform.position : pz ? pz.transform.position : g.At(id);
            var exit = AreaSystem.I != null ? AreaSystem.I.ExitToward(raw) : null;
            if (exit != null) { viaExit = true; return Game.Ground(new Vector3(exit.Pos.x, 0, exit.Pos.y)); }
            if (n) { follow = n.transform; return n.transform.position; }
            if (pz) { var it = pz.GetComponentInChildren<Interactable>(); follow = it ? it.transform : pz.transform; return follow.position; }
            var item = Interactable.All.FirstOrDefault(x => x.id == id);
            if (item) { follow = item.transform; return item.transform.position; }
            return g.At(id);
        }

        void Update()
        {
            var g = G;
            if (g == null || g.ui == null || !g.ui.Bound || marker == null) return;
            if (Input.GetKeyDown(KeyCode.F2)) devMarker = !devMarker;
            var goal = g.Data.CurrentGoal(g.State);
            string goalKey = goal?.Text ?? "";
            int flags = g.State.Flags.Count();
            if (goalKey != lastGoal || flags != lastFlagCount) { lastGoal = goalKey; lastFlagCount = flags; idle = 0; stage = 0; }
            bool free = !g.Busy && !g.ui.BlocksWorld && !g.PickMode;
            // 걷고 있으면 탐색 중 — 조금만 셈(서 있을 때 더 빨리 도움)
            if (free) idle += Time.deltaTime * (g.player.IsMoving ? 0.5f : 1f);

            var pt = TargetPoint(out var follow, out var viaExit);
            marker.gameObject.SetActive(devMarker && pt.HasValue && free);
            if (marker.gameObject.activeSelf) { marker.position = pt.Value + Vector3.up * 2f; var cam = Camera.main; if (cam) marker.rotation = Quaternion.LookRotation(marker.position - cam.transform.position); }
            if (!free || !pt.HasValue) return;

            // ① 가까우면 은은한 반짝임
            nearGlint -= Time.deltaTime;
            if (nearGlint <= 0f && follow && Vector3.Distance(g.player.transform.position, pt.Value) < 7f)
            {
                nearGlint = 4f;
                foreach (var it in follow.GetComponentsInChildren<Interactable>()) if (it.available && it.kind != Interactable.Kind.Npc) it.Pulse(0.9f);
            }

            if (stage == 0 && idle > glintAt) { stage = 1; Glint(goal, follow); }
            else if (stage == 1 && idle > kidAt) { stage = 2; StartCoroutine(KidShows(pt.Value, TargetId(goal))); }
            else if (stage == 2 && idle > thoughtAt) { stage = 3; var th = goal?.Raw != null ? J.Str(goal.Raw, "thought") : null; if (!string.IsNullOrEmpty(th)) g.ui.ShowThought(th, 3.5f); }
        }

        void Glint(GoalDef goal, Transform follow)
        {
            var id = TargetId(goal);
            if (follow) foreach (var it in follow.GetComponentsInChildren<Interactable>()) it.Pulse(3.5f);
            foreach (var it in Interactable.All.Where(x => x.id == id)) it.Pulse(3.5f);
            AudioHub.Play("almost", 0.25f, 1.3f);
        }

        /// <summary>키노피오가 대상 쪽으로 몇 걸음 가서 가리키고 주인공을 돌아봄(대상이 키노피오면 손짓만).</summary>
        System.Collections.IEnumerator KidShows(Vector3 target, string id)
        {
            var g = G;
            var kid = g.Npc("kinopio");
            if (!kid || !kid.gameObject.activeInHierarchy || kid.Leading) yield break;
            if (AreaSystem.I != null && !AreaSystem.I.InActive(kid.transform.position)) yield break;
            if (id == "kinopio")
            {
                kid.LookAt(g.player.transform.position); kid.SetPose(ProceduralRig.Pose.Point);
                AudioHub.Play("speak", 0.3f, 1.5f);
                yield return new WaitForSeconds(1.4f); kid.SetPose(ProceduralRig.Pose.Stand);
                yield break;
            }
            // 갈 수 없는 곳(틈 아래에서 올려다보는 사다리 등)이면 그 자리에서 가리키기만
            var path = new UnityEngine.AI.NavMeshPath();
            if (!UnityEngine.AI.NavMesh.CalculatePath(kid.transform.position, target, UnityEngine.AI.NavMesh.AllAreas, path) || path.status != UnityEngine.AI.NavMeshPathStatus.PathComplete)
            {
                kid.LookAt(target); kid.SetPose(ProceduralRig.Pose.PointUp); AudioHub.Play("speak", 0.25f, 1.6f);
                yield return new WaitForSeconds(1.6f);
                kid.LookAt(g.player.transform.position); kid.SetPose(ProceduralRig.Pose.LookUp);
                yield break;
            }
            bool wasFollowing = kid.Following;
            var home = kid.transform.position;
            var step = Vector3.MoveTowards(home, target, Mathf.Min(4f, Vector3.Distance(home, target) - 1.2f));
            bool done = false;
            kid.WalkTo(step, () => done = true);
            float t = 0; while (!done && t < 5f) { t += Time.deltaTime; yield return null; }
            kid.LookAt(target); kid.SetPose(ProceduralRig.Pose.Point);
            yield return new WaitForSeconds(1.3f);
            kid.LookAt(g.player.transform.position);
            yield return new WaitForSeconds(1.0f);
            kid.SetPose(ProceduralRig.Pose.Stand);
            if (wasFollowing) kid.Follow(g.player.transform);
        }
    }
}
