using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using OUAT.World;
using UnityEngine;

namespace OUAT.Core
{
    /// <summary>
    /// 구역(장면) 체계 — 세나르처럼 맵이 구역으로 나뉘고 출구로 가면 다음 구역으로 넘어간다(결정장부 화-12).
    /// 구역 하나 = 그림책 한 쪽: 지금 구역만 그리고, 넘어갈 때 책장을 넘긴다. 데이터는 chapter1.json areas[].
    /// 그리기 끄기는 Renderer.forceRenderingOff만 쓴다(다른 연출이 쓰는 enabled와 겹치지 않게).
    /// </summary>
    public class AreaSystem : MonoBehaviour
    {
        public static AreaSystem I { get; private set; }
        public string Active { get; private set; }
        public event Action<string> AreaChanged;

        Game G => Game.I;
        readonly List<(Renderer r, string area)> staticRenderers = new List<(Renderer, string)>();
        readonly List<(Light l, string area)> staticLights = new List<(Light, string)>();
        // 안 보이는 구역의 충돌체가 마우스 광선을 가로채면 포인터가 엉뚱한 곳을 가리킨다(사용자 “포인터가 안맞거나”) — 구역과 함께 끔
        readonly List<(Collider c, string area)> staticColliders = new List<(Collider, string)>();
        readonly List<(Transform root, Renderer[] rs, Light[] ls)> dynamic = new List<(Transform, Renderer[], Light[])>();
        float exitCooldown, refreshTimer;
        bool transitioning;

        void Awake() { I = this; }

        void Start()
        {
            var g = G;
            if (g == null || g.Data.Areas.Count == 0) { enabled = false; return; }
            var dynRoots = new HashSet<Transform>();
            dynRoots.Add(g.player.transform);
            foreach (var n in g.AllNpcs) dynRoots.Add(n.transform);
            if (g.director && g.director.fish) dynRoots.Add(g.director.fish.transform);
            foreach (var p in PropState.All.Values) dynRoots.Add(p.transform);
            foreach (var root in dynRoots) dynamic.Add((root, root.GetComponentsInChildren<Renderer>(true), root.GetComponentsInChildren<Light>(true)));

            foreach (var r in FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (dynRoots.Any(d => r.transform.IsChildOf(d))) continue;
                staticRenderers.Add((r, AreaOfTransform(r.transform, r.bounds.center)));
            }
            foreach (var c in FindObjectsByType<Collider>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (!c.enabled || c.isTrigger || dynRoots.Any(d => c.transform.IsChildOf(d))) continue;
                if (c.GetComponentInParent<Interactable>() != null && c.GetComponentInParent<PropState>() != null) continue;   // 물건은 동적 목록이 맡음
                staticColliders.Add((c, AreaOfTransform(c.transform, c.bounds.center)));
            }
            foreach (var l in FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (l.type == LightType.Directional || dynRoots.Any(d => l.transform.IsChildOf(d))) continue;
                staticLights.Add((l, AreaOfTransform(l.transform, l.transform.position)));
            }
            SetActive(Of(g.player.transform.position), snap: true);
        }

        /// <summary>계층에 Area_&lt;id&gt; / Global 이 있으면 그것, 아니면 위치로.</summary>
        string AreaOfTransform(Transform t, Vector3 pos)
        {
            for (var p = t; p != null; p = p.parent)
            {
                if (p.name == "Global" || p.name.StartsWith("Global_") || p.name.StartsWith("Backdrop") || p.name.StartsWith("Ceiling")) return null;
                if (p.name.StartsWith("Area_")) { var id = p.name.Substring(5); if (G.Data.Areas.ContainsKey(id)) return id; }
            }
            return Of(pos);
        }

        public string Of(Vector3 p)
        {
            var g = G; if (g == null) return null;
            var v = new Vector2(p.x, p.z);
            string best = null; float bd = float.MaxValue;
            foreach (var a in g.Data.Areas.Values) { float d = a.SignedDistance(v); if (d < bd) { bd = d; best = a.Id; } }
            return best;
        }

        public AreaDef Def(string id) => id != null && G.Data.Areas.TryGetValue(id, out var a) ? a : null;

        public void SetActive(string id, bool snap)
        {
            Active = id;
            foreach (var (r, area) in staticRenderers) if (r) r.forceRenderingOff = area != null && area != id;
            foreach (var (l, area) in staticLights) if (l) l.gameObject.SetActive(area == null || area == id);
            foreach (var (c, area) in staticColliders) if (c) c.enabled = area == null || area == id;
            RefreshDynamic();
            ApplyMood(id);
            var a = Def(id);
            var fc = G.followCamera;
            if (a != null && fc)
            {
                if (a.Camera != null)
                    fc.baseView = new FollowCamera.View { yaw = J.F(a.Camera["yaw"]), pitch = J.F(a.Camera["pitch"]), distance = J.F(a.Camera["distance"]), fov = a.Camera.ContainsKey("fov") ? J.F(a.Camera["fov"]) : 32f, offset = new Vector3(0, 0.6f, 0) };
                fc.SetBounds(a.Bounds);
                if (snap) fc.SnapToTarget();
            }
            AreaChanged?.Invoke(id);
        }

        // ── 구역 분위기: 땅 밑 세계. 빛구멍 언덕만 빛줄기로 밝고, 나머지는 어둑하고 색이 빠짐(검은 밤·안개 아님) — 사용자 10/23 ──
        public struct Mood { public Color ambient, key, bg; public float keyIntensity, drain; }
        static readonly Dictionary<string, Mood> Moods = new Dictionary<string, Mood>
        {
            { "a_fall",  new Mood { ambient = new Color(0.19f, 0.195f, 0.215f), key = new Color(0.79f, 0.81f, 0.85f), keyIntensity = 0.30f, drain = 0.45f, bg = new Color(0.30f, 0.31f, 0.32f) } },
            { "a_gate",  new Mood { ambient = new Color(0.21f, 0.215f, 0.235f), key = new Color(0.79f, 0.81f, 0.85f), keyIntensity = 0.32f, drain = 0.55f, bg = new Color(0.30f, 0.31f, 0.32f) } },
            { "a_cart",  new Mood { ambient = new Color(0.20f, 0.205f, 0.225f), key = new Color(0.72f, 0.75f, 0.80f), keyIntensity = 0.30f, drain = 0.60f, bg = new Color(0.28f, 0.29f, 0.30f) } },
            { "a_plaza", new Mood { ambient = new Color(0.26f, 0.24f, 0.22f), key = new Color(0.86f, 0.78f, 0.66f), keyIntensity = 0.38f, drain = 0.30f, bg = new Color(0.32f, 0.30f, 0.28f) } },
            { "a_alley", new Mood { ambient = new Color(0.21f, 0.20f, 0.21f), key = new Color(0.74f, 0.72f, 0.74f), keyIntensity = 0.30f, drain = 0.48f, bg = new Color(0.28f, 0.27f, 0.27f) } },
            { "a_hideout", new Mood { ambient = new Color(0.28f, 0.24f, 0.20f), key = new Color(0.90f, 0.78f, 0.60f), keyIntensity = 0.30f, drain = 0.25f, bg = new Color(0.25f, 0.22f, 0.20f) } },
            { "a_field", new Mood { ambient = new Color(0.18f, 0.185f, 0.20f), key = new Color(0.70f, 0.74f, 0.80f), keyIntensity = 0.28f, drain = 0.62f, bg = new Color(0.24f, 0.25f, 0.27f) } },
        };
        Light keyLight;

        void ApplyMood(string id)
        {
            if (id == null || !Moods.TryGetValue(id, out var m)) return;
            var a = Def(id);
            // 데이터의 mood는 "override": true일 때만(지형 담당이 블렌더 흉내로 잰 배수라 코드 값과 겹쳐 두 번 어두워짐)
            if (a?.Raw != null && a.Raw.TryGetValue("mood", out var mo) && mo is Dictionary<string, object> md && J.Bool(md, "override", false))
            {
                if (md.TryGetValue("drain", out var dr)) m.drain = J.F(dr);
                if (md.TryGetValue("keyIntensity", out var ki)) m.keyIntensity = J.F(ki);
                if (md.TryGetValue("ambient", out var am)) m.ambient *= J.F(am);
            }
            Shader.SetGlobalColor("_OUAT_Ambient", new Color(m.ambient.r, m.ambient.g, m.ambient.b, 1f));
            Shader.SetGlobalFloat("_OUAT_Drain", m.drain);
            Shader.SetGlobalColor("_OUAT_DrainTint", new Color(0.97f, 0.95f, 0.92f, 1f));
            Shader.SetGlobalColor("_OUAT_EdgeColor", new Color(m.bg.r, m.bg.g, m.bg.b, 1f));
            RenderSettings.ambientLight = m.ambient;
            if (!keyLight) keyLight = FindObjectsByType<Light>(FindObjectsSortMode.None).FirstOrDefault(l => l.type == LightType.Directional);
            if (keyLight) { keyLight.color = m.key; keyLight.intensity = m.keyIntensity; }
            var cam = Camera.main;
            if (cam) cam.backgroundColor = m.bg;
            // 구역 바탕 소리(소리 담당 표): 굴 = amb_hideout, 골목·길목·창고 = amb_alley, 광장 = amb_plaza, 언덕·밭 = ambient
            AudioHub.Ambient(id == "a_hideout" ? "amb_hideout" : id == "a_plaza" ? "amb_plaza" : id == "a_alley" || id == "a_gate" || id == "a_cart" ? "amb_alley" : "ambient");
        }

        void RefreshDynamic()
        {
            foreach (var (root, rs, ls) in dynamic)
            {
                if (!root) continue;
                bool on = Of(root.position) == Active || root == G.player.transform;
                foreach (var r in rs) if (r) r.forceRenderingOff = !on;
                foreach (var l in ls) if (l) l.enabled = on;
            }
        }

        public bool InActive(Vector3 p) => Of(p) == Active;

        void Update()
        {
            var g = G;
            if (g == null || g.ui == null || !g.ui.Bound || Active == null) return;
            refreshTimer -= Time.deltaTime;
            if (refreshTimer <= 0f) { refreshTimer = 0.25f; RefreshDynamic(); }
            exitCooldown -= Time.deltaTime;
            if (transitioning || g.Busy || g.ui.BlocksWorld || exitCooldown > 0f) return;
            var a = Def(Active); if (a == null) return;
            var p = g.player.transform.position; var v = new Vector2(p.x, p.z);
            foreach (var e in a.Exits)
                if (Vector2.Distance(v, e.Pos) <= e.Radius && g.player.Agent.velocity.sqrMagnitude > 0.05f)
                {
                    var lockReact = LockedReact(Active, e.To);
                    if (lockReact != null)
                    {
                        // 잠긴 출구: 넘어가지 않고 주인공 반응 한 번(2초에 한 번), 한 걸음 물러섬
                        exitCooldown = 2f;
                        g.player.Stop();
                        var ep = new Vector3(e.Pos.x, p.y, e.Pos.y);
                        var back = p + (p - ep).normalized * 0.9f;
                        g.player.WalkTo(back);
                        if (lockReact.Length > 0 && g.director) StartCoroutine(g.director.React("hero", lockReact));
                        break;
                    }
                    StartCoroutine(Go(e)); break;
                }
        }

        /// <summary>exitLocks[]: 그 출구가 지금 잠겼으면 반응 이름(없으면 ""), 열렸으면 null.</summary>
        public string LockedReact(string from, string to)
        {
            foreach (var l in G.Data.ExitLocks)
            {
                if (J.Str(l, "area") != from || J.Str(l, "to") != to) continue;
                if (Condition.From(l.TryGetValue("locked", out var c) ? c : null).Eval(G.State)) return J.Str(l, "react", "");
            }
            return null;
        }

        /// <summary>출구 근처 땅을 눌렀으면 출구, 구역 밖을 눌렀으면 구역 안 가장 가까운 곳.</summary>
        public Vector3 ResolveClick(Vector3 point, out AreaExit exit)
        {
            exit = null;
            var a = Def(Active); if (a == null) return point;
            var v = new Vector2(point.x, point.z);
            foreach (var e in a.Exits) if (Vector2.Distance(v, e.Pos) < e.Radius + 2.2f) { exit = e; return Game.Ground(new Vector3(e.Pos.x, 0, e.Pos.y)); }
            if (a.SignedDistance(v) <= -0.4f) return point;
            // 구역 안쪽으로 당김(모양 경계를 따라 조금씩)
            var c = a.Shapes[0].Line != null ? a.Shapes[0].Line[0] : a.Shapes[0].C;
            for (int i = 0; i < 40 && a.SignedDistance(v) > -0.4f; i++) v = Vector2.MoveTowards(v, NearestInside(a, v), 0.5f);
            return Game.Ground(new Vector3(v.x, 0, v.y));
        }

        static Vector2 NearestInside(AreaDef a, Vector2 v)
        {
            Vector2 best = v; float bd = float.MaxValue;
            foreach (var s in a.Shapes)
            {
                Vector2 q;
                if (s.Line != null && s.Line.Count > 1)
                {
                    q = s.Line[0]; float qd = float.MaxValue;
                    for (int i = 0; i < s.Line.Count - 1; i++)
                    {
                        var x = s.Line[i]; var ab = s.Line[i + 1] - x;
                        var pt = x + ab * Mathf.Clamp01(Vector2.Dot(v - x, ab) / Mathf.Max(1e-4f, ab.sqrMagnitude));
                        float dd = Vector2.Distance(v, pt); if (dd < qd) { qd = dd; q = pt; }
                    }
                }
                else q = s.C;
                float d = Vector2.Distance(v, q); if (d < bd) { bd = d; best = q; }
            }
            return best;
        }

        public AreaExit ExitNear(Vector3 point, float extra = 2.2f)
        {
            var a = Def(Active); if (a == null) return null;
            var v = new Vector2(point.x, point.z);
            return a.Exits.FirstOrDefault(e => Vector2.Distance(v, e.Pos) < e.Radius + extra);
        }

        IEnumerator Go(AreaExit e)
        {
            transitioning = true;
            var g = G;
            g.Busy = true;
            g.player.Stop();
            var target = Def(e.To);
            var kid = g.Npc("kinopio");
            bool kidFollows = kid && (kid.Following || kid.Leading);
            yield return g.ui.PageTurn(() =>
            {
                var spawn = Game.Ground(new Vector3(e.Spawn.x, 0, e.Spawn.y));
                g.player.Warp(spawn);
                g.player.transform.rotation = Quaternion.Euler(0, e.Face, 0);
                if (kidFollows)
                {
                    bool leading = kid.Leading;
                    kid.Warp(spawn + (leading ? 1.6f : -1.6f) * g.player.transform.forward + g.player.transform.right * 0.8f);
                    if (!leading) kid.Follow(g.player.transform);
                }
                SetActive(e.To, snap: true);
                if (kidFollows && kid.Leading) g.Relead(kid);
            }, target != null ? target.Name : "");
            exitCooldown = 1.0f;
            g.Busy = false;
            transitioning = false;
            g.Fire("area:" + e.To);
            g.Save();
        }

        /// <summary>크리처를 다른 구역의 자리로: 지금 구역에 보이면 출구까지 걸어 나간 뒤 옮기고, 아니면 바로 옮긴다.</summary>
        public IEnumerator Route(NpcActor n, Vector3 target, Action arrive)
        {
            var from = Of(n.transform.position); var to = Of(target);
            if (from == to) { n.WalkTo(target, arrive, routed: true); yield break; }
            if (from == Active)
            {
                var hop = NextHop(from, to);
                var ex = Def(from).Exits.FirstOrDefault(x => x.To == hop);
                if (ex != null)
                {
                    bool done = false;
                    n.WalkTo(Game.Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y)), () => done = true, routed: true);
                    float t = 0; while (!done && t < 20f) { t += Time.deltaTime; yield return null; }
                }
            }
            n.Warp(target);
            arrive?.Invoke();
        }

        /// <summary>다른 구역에 있는 목표로 가려면 지금 구역의 어느 출구로 나가야 하나.</summary>
        public AreaExit ExitToward(Vector3 target)
        {
            var to = Of(target);
            if (to == null || to == Active) return null;
            var hop = NextHop(Active, to);
            return Def(Active)?.Exits.FirstOrDefault(x => x.To == hop);
        }

        string NextHop(string from, string to)
        {
            var prev = new Dictionary<string, string> { [from] = null };
            var q = new Queue<string>(); q.Enqueue(from);
            while (q.Count > 0)
            {
                var c = q.Dequeue();
                if (c == to) break;
                foreach (var e in Def(c).Exits) if (!prev.ContainsKey(e.To)) { prev[e.To] = c; q.Enqueue(e.To); }
            }
            if (!prev.ContainsKey(to)) return to;
            var step = to; while (prev[step] != from && prev[step] != null) step = prev[step];
            return step;
        }
    }
}
