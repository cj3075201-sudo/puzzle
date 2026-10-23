using System.Collections;
using System.Collections.Generic;
using System.Linq;
using OUAT.Core;
using UnityEngine;

namespace OUAT.World
{
    /// <summary>
    /// 데이터 props[]의 물건 하나와 그 상태(사다리 folded/unfolded, 수레 loaded_stuck/at_pond …).
    /// 상태 이름과 같은 이름의 자식(state_&lt;이름&gt;)이 있으면 그것만 켜고, 물건마다 필요한 움직임은 Apply에서 한다.
    /// 표에 없는 물건은 일반 규칙: 상태 hidden이면 숨김, 그 밖이면 보임.
    /// </summary>
    public class PropState : MonoBehaviour
    {
        public string propId;
        public string state;
        [Tooltip("인물 뼈에 붙은 물건(props[].attach) — 숨길 때 자식을 끔(주인공 보이기가 렌더러를 다시 켜도 안 나타나게)")] public bool attached;
        [Tooltip("물건 밖에 있지만 같이 켜고 끄는 것(길 따라 놓인 부스러기·횃불, 주인공 몸의 가방 메시)")] public GameObject[] linked;
        [Tooltip("이 깃발이 모두 서야 보임(읽을거리 visibleWhen.all)")] public string[] visibleAll;
        public static readonly Dictionary<string, PropState> All = new Dictionary<string, PropState>();
        Vector3 homePos; Quaternion homeRot;
        readonly Dictionary<Transform, (Vector3 p, Quaternion r, Vector3 s)> restParts = new Dictionary<Transform, (Vector3, Quaternion, Vector3)>();
        bool hidden;
        float doorSign = 1f;
        Coroutine swing;

        void Awake()
        {
            All[propId] = this;
            homePos = transform.position; homeRot = transform.rotation;
            foreach (var t in GetComponentsInChildren<Transform>(true)) restParts[t] = (t.localPosition, t.localRotation, t.localScale);
            // 문 경첩 쪽: 문판이 경첩의 +X 쪽에 있으면 +로 돌려야 안쪽(−Z)으로 열림
            var door = Part("Door");
            var dr = door ? door.GetComponentInChildren<Renderer>() : null;
            if (dr) doorSign = transform.InverseTransformPoint(dr.bounds.center).x >= transform.InverseTransformPoint(door.position).x ? 1f : -1f;
        }

        void Start()
        {
            if (visibleAll != null && visibleAll.Length > 0 && Game.I != null) { Game.I.StateRefreshed += RefreshVisible; RefreshVisible(); }
        }

        void OnDestroy()
        {
            if (All.TryGetValue(propId, out var p) && p == this) All.Remove(propId);
            if (Game.I != null) Game.I.StateRefreshed -= RefreshVisible;
        }

        void RefreshVisible() { var g = Game.I; if (g != null && g.State != null) Visible(visibleAll.All(g.State.Has)); }

        Transform Part(string name)
        {
            foreach (var t in GetComponentsInChildren<Transform>(true))
                if (t != transform && (t.name == name || t.name.StartsWith(name + ".") || t.name.EndsWith("_" + name) || t.name.StartsWith(name + "_"))) return t;
            return null;
        }

        public void Set(string s, bool animate)
        {
            state = s;
            // 상태 이름과 같은 자식: 그것만 보이기
            var stateChildren = new List<Transform>();
            foreach (Transform c in transform) if (c.name.StartsWith("state_")) stateChildren.Add(c);
            foreach (var c in stateChildren) c.gameObject.SetActive(c.name == "state_" + s);
            if (isActiveAndEnabled && animate) StartCoroutine(Apply(s, true));
            else { var e = Apply(s, false); while (e.MoveNext()) { } }
        }

        IEnumerator Tween(Transform t, Vector3? pos, Quaternion? rot, Vector3? scale, float seconds, bool animate)
        {
            if (t == null) yield break;
            var p0 = t.localPosition; var r0 = t.localRotation; var s0 = t.localScale;
            if (!animate || seconds <= 0f)
            {
                if (pos.HasValue) t.localPosition = pos.Value; if (rot.HasValue) t.localRotation = rot.Value; if (scale.HasValue) t.localScale = scale.Value;
                yield break;
            }
            float k = 0;
            while (k < 1f)
            {
                k += Time.deltaTime / seconds;
                float e = 1f - Mathf.Pow(1f - Mathf.Clamp01(k), 3f);
                if (pos.HasValue) t.localPosition = Vector3.LerpUnclamped(p0, pos.Value, e);
                if (rot.HasValue) t.localRotation = Quaternion.SlerpUnclamped(r0, rot.Value, e);
                if (scale.HasValue) t.localScale = Vector3.LerpUnclamped(s0, scale.Value, e);
                yield return null;
            }
        }

        IEnumerator WorldMove(Vector3 to, float seconds, bool animate)
        {
            if (!animate) { transform.position = to; yield break; }
            var from = transform.position; float k = 0;
            while (k < 1f)
            {
                k += Time.deltaTime / seconds;
                float e = Mathf.SmoothStep(0, 1, k);
                transform.position = Vector3.Lerp(from, to, e) + Vector3.up * Mathf.Abs(Mathf.Sin(k * 40f)) * 0.03f;
                yield return null;
            }
        }

        Vector3 Rest(Transform t) => restParts.TryGetValue(t, out var r) ? r.p : t.localPosition;
        Quaternion RestRot(Transform t) => restParts.TryGetValue(t, out var r) ? r.r : t.localRotation;
        Vector3 RestScale(Transform t) => restParts.TryGetValue(t, out var r) ? r.s : t.localScale;

        void Show(string part, bool on) { var p = Part(part); if (p) p.gameObject.SetActive(on); }

        /// <summary>보이기/숨기기 — 바뀔 때만(지은 그대로 꺼 둔 렌더러를 함부로 켜지 않게).</summary>
        void Visible(bool on) { if (on == !hidden) return; hidden = !on; ShowSelf(on); }

        void ShowSelf(bool on)
        {
            if (attached) foreach (Transform c in transform) c.gameObject.SetActive(on);
            else
            {
                foreach (var r in GetComponentsInChildren<Renderer>(true)) r.enabled = on;
                foreach (var c in GetComponentsInChildren<Collider>(true)) if (!c.isTrigger) c.enabled = on;
                // 구역 시스템이 Light.enabled를 매번 다시 켜므로 등은 오브젝트째 끔
                foreach (var l in GetComponentsInChildren<Light>(true)) if (l.gameObject != gameObject) l.gameObject.SetActive(on);
            }
            if (linked == null) return;
            foreach (var g in linked)
            {
                if (!g) continue;
                if (attached) { g.SetActive(on); continue; }
                foreach (var r in g.GetComponentsInChildren<Renderer>(true)) r.enabled = on;
                foreach (var l in g.GetComponentsInChildren<Light>(true)) l.enabled = on;   // 구역 시스템은 정적 등을 오브젝트째 끄고 켬 — 여기선 enabled
            }
        }

        IEnumerator Apply(string s, bool animate)
        {
            switch (propId)
            {
                case "ladder":
                {
                    var upper = Part("Upper");
                    if (upper) yield return Tween(upper, null, RestRot(upper) * (s == "unfolded" ? Quaternion.Euler(180, 0, 0) : Quaternion.identity), null, 1.1f, animate);
                    if (s == "unfolded") AudioHub.Play("latch", 0.8f, 0.8f);
                    foreach (var o in GetComponentsInChildren<UnityEngine.AI.NavMeshObstacle>(true)) o.enabled = s != "unfolded";
                    break;
                }
                case "bolt_fall":
                {
                    var bar = Part("Bar") ?? transform;
                    var lifted = s == "lifted";
                    yield return Tween(bar, Rest(bar) + (lifted ? Vector3.up * 1.4f : Vector3.zero), RestRot(bar) * (lifted ? Quaternion.Euler(0, 0, 70) : Quaternion.identity), null, 0.7f, animate);
                    foreach (var o in GetComponentsInChildren<UnityEngine.AI.NavMeshObstacle>(true)) o.enabled = !lifted;
                    break;
                }
                case "lump_prop":
                    Visible(s == "onchair");
                    break;
                case "cart":
                {
                    var items = Part("Items") ?? Part("CartItems");
                    bool loaded = s == "loaded_stuck" || s == "loaded_day" || s == "at_pond" || s == "day_at_pond";
                    if (items) items.gameObject.SetActive(loaded);
                    if (s == "at_pond" || s == "day_at_pond")
                    {
                        var g = Game.I;
                        var target = g != null ? g.ZonePoint("z_pond_edge") : homePos;
                        AudioSource loop = null;
                        if (animate)
                        {
                            var clip = Resources.Load<AudioClip>("Audio/cart");
                            if (clip) { loop = gameObject.AddComponent<AudioSource>(); loop.clip = clip; loop.loop = true; loop.volume = 0.55f; loop.spatialBlend = 0.6f; loop.Play(); }
                        }
                        yield return WorldMove(new Vector3(target.x, homePos.y, target.z), 4.5f, animate);
                        if (loop) Destroy(loop);
                        if (g != null) g.SetProp("tracks", "visible");
                    }
                    else if (s == "empty" || s == "loaded_stuck" || s == "loaded_day") { if (!animate) transform.position = homePos; }
                    if (s == "emptied")
                    {
                        if (items) items.gameObject.SetActive(false);
                        var g2 = Game.I; if (g2 != null && !animate) { var t2 = g2.ZonePoint("z_pond_edge"); transform.position = new Vector3(t2.x, homePos.y, t2.z); }
                    }
                    break;
                }
                case "tracks":
                    Visible(s == "visible");
                    break;
                case "pond":
                {
                    var surf = Part("Surface");
                    if (surf) surf.GetComponent<PondSurface>()?.SetAwake(s == "awake");
                    break;
                }
                case "stage":
                {
                    if (animate) AudioHub.Play("curtain", 0.6f);
                    var curtain = Part("Curtain") ?? Part("CurtainL");
                    foreach (var l in GetComponentsInChildren<Light>(true)) l.gameObject.SetActive(s == "ceremony");
                    if (curtain) yield return Tween(curtain, Rest(curtain), null, RestScale(curtain), 0.6f, animate);
                    break;
                }
                case "sack":
                    // 닫힌 자루는 주인공이 선 자리에(주인공을 담음) — 불러오기 때는 제자리
                    if (s == "closed" && animate && Game.I != null && Game.I.player) transform.position = Game.I.player.transform.position;
                    Visible(s != "hidden");
                    break;
                case "bell":
                {
                    // 종(Bell_plaza / BellBody, 피벗 = 매단 점)을 로컬 X로 ±15° — ring 동안 흔들리다 잦아듦
                    var bell = Part("BellBody") ?? Part("Bell_plaza");
                    if (s == "ring" && bell && animate && isActiveAndEnabled) { if (swing != null) StopCoroutine(swing); swing = StartCoroutine(Swing(bell)); }
                    else if (s != "ring" && bell && !animate) bell.localRotation = RestRot(bell);
                    break;
                }
                case "band_new":
                    Visible(s != "hidden");
                    Show("Face", s != "peeled");   // 벗기면 크리처 띠(Face)가 사라지고 밑의 사람 글(HumanText)이 드러남
                    break;
                case "bark_door":
                {
                    var door = Part("Door");
                    bool open = s == "open";
                    if (open && animate) AudioHub.Play("latch", 0.5f, 0.7f);
                    foreach (var o in GetComponentsInChildren<UnityEngine.AI.NavMeshObstacle>(true)) o.enabled = !open;
                    if (door) yield return Tween(door, null, RestRot(door) * Quaternion.Euler(0, open ? 100f * doorSign : 0f, 0), null, 1.0f, animate);
                    break;
                }
                case "brother_lump":
                    if (s == "uncovered" && animate) AudioHub.Play("sack", 0.4f, 1.2f);
                    Show("Cover", s != "uncovered");
                    break;
                case "cord_basket":
                {
                    var lid = Part("Lid");
                    if (lid) yield return Tween(lid, null, RestRot(lid) * (s == "open" ? Quaternion.Euler(-105, 0, 0) : Quaternion.identity), null, 0.6f, animate);
                    break;
                }
                case "wall_drawing":
                case "wall_hero":
                    RefreshWall();
                    break;
                case "hero_cord":
                    Visible(s == "once" || s == "twice");
                    Show("Loop2", s == "twice");   // 두 번 감음 = 둘째 고리
                    break;
                case "door_nose":
                    // long = 갈지 못한 긴 코끝, short = 조각(Piece)이 떨어져 문 앞에 누움(Fallen)
                    Visible(s != "hidden");
                    Show("Piece", s == "long");
                    Show("Fallen", s == "short");
                    if (s == "short" && animate) AudioHub.Play("drop", 0.3f, 1.4f);
                    break;
                case "hero_bag":
                case "satchel":
                    Visible(s != "taken");
                    break;
                default:
                    Visible(s != "hidden");
                    break;
            }
        }

        IEnumerator Swing(Transform bell)
        {
            var r0 = RestRot(bell);
            float k = 0f, fade = 0f;
            while (fade < 1f)
            {
                k += Time.deltaTime;
                if (state != "ring" && k > 2f) fade += Time.deltaTime / 1.2f;
                float a = 15f * Mathf.Sin(k * Mathf.PI * 2f / 1.1f) * (1f - fade) * Mathf.Clamp01(k * 3f);
                bell.localRotation = r0 * Quaternion.Euler(a, 0, 0);
                yield return null;
            }
            bell.localRotation = r0;
            swing = null;
        }

        /// <summary>굴 벽 숯 그림: plain = wall_drawing(망토 아이가 들어가면 _3), line = _line, smudge = _rubbed.</summary>
        static void RefreshWall()
        {
            if (!All.TryGetValue("wall_drawing", out var w)) return;
            bool hero = All.TryGetValue("wall_hero", out var h) && h.state == "shown";
            var pic = w.state == "line" ? "wall_drawing_line" : w.state == "smudge" ? "wall_drawing_rubbed" : hero ? "wall_drawing_3" : "wall_drawing";
            var face = w.Part("Face");
            var r = face ? face.GetComponent<Renderer>() : null;
            var tex = Resources.Load<Texture2D>("Pictures/" + pic);
            if (r && tex && Application.isPlaying) r.material.SetTexture("_BaseMap", tex);
        }

        public void ResetHome() { transform.position = homePos; transform.rotation = homeRot; }
    }
}
