using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using OUAT.Jigsaw;
using OUAT.UI;
using OUAT.World;
using UnityEngine;

namespace OUAT.Core
{
    /// <summary>
    /// 1챕터 진행의 중심. chapter1.json의 사건(events)을 실행하고, 장소·구역 출입/가까이 감/말 걸기/대화 결과/퍼즐/읽기/장면 끝을
    /// 사건 이름(enter:·leave:·near:·talk:·done:·puzzle:·read:·sceneEnd:·playEnd:·flag:)으로 바꿔 알린다.
    /// 단계(phases)에 맞춰 크리처 자리를 옮기고, 머리 위 말·화면 목표·물건 상태·저장을 맞춘다.
    /// </summary>
    public class Game : MonoBehaviour
    {
        public static Game I { get; private set; }

        [Header("장면 연결")]
        public PlayerMover player;
        public FollowCamera followCamera;
        public UIRoot ui;
        public Director director;

        public ChapterData Data { get; private set; }
        public ModelLibrary Models { get; private set; }
        public GameState State { get; private set; }
        public HashSet<string> Blue { get; private set; }

        readonly Dictionary<string, NpcActor> npcs = new Dictionary<string, NpcActor>();
        readonly Dictionary<string, Interactable> inscriptions = new Dictionary<string, Interactable>();
        readonly Dictionary<string, PuzzleObject> puzzles = new Dictionary<string, PuzzleObject>();
        readonly Queue<string> pendingTriggers = new Queue<string>();
        readonly HashSet<string> insideZones = new HashSet<string>();
        readonly HashSet<string> nearNpcs = new HashSet<string>();
        readonly Dictionary<string, int> dialogueFails = new Dictionary<string, int>();
        bool runningEvents;
        Interactable hovered;
        string currentPhase;
        Coroutine rehearsal;
        int busyCount;

        // 연출 중(입력 막음) 카운터 — 누가 켰는지 기록해 새는 곳을 찾고, 오래 새면 풀어 줌(자동 완주 10/23: 사다리 뒤 계속 켜져 구역이 안 넘어감)
        readonly List<string> busyOwners = new List<string>();
        float busySince;
        public string BusyOwners => string.Join(",", busyOwners);
        public bool Busy
        {
            get => busyCount > 0;
            set
            {
                if (value)
                {
                    if (busyCount == 0) busySince = Time.time;
                    busyCount++;
                    var f = new System.Diagnostics.StackTrace(1).GetFrame(0)?.GetMethod();
                    busyOwners.Add(f != null ? f.DeclaringType?.Name + "." + f.Name : "?");
                }
                else
                {
                    busyCount = Mathf.Max(0, busyCount - 1);
                    if (busyOwners.Count > 0) busyOwners.RemoveAt(busyOwners.Count - 1);
                    if (busyCount == 0) busyOwners.Clear();
                }
            }
        }

        /// <summary>연출 중이 너무 오래(60초) 이어지는데 돌고 있는 사건·열린 화면이 없으면 새는 것으로 보고 풂.</summary>
        void BusyWatchdog()
        {
            if (busyCount <= 0 || runningEvents || ui == null || ui.BlocksWorld || PickMode) { if (busyCount <= 0) busySince = Time.time; return; }
            if (Time.time - busySince < 60f) return;
            Debug.LogWarning($"[OUAT] 연출 중이 60초 넘게 풀리지 않아 풂: {BusyOwners}");
            busyCount = 0; busyOwners.Clear(); busySince = Time.time;
        }
        public bool PickMode { get; private set; }
        public event Action StateRefreshed;

        void Awake()
        {
            I = this;
            var chapterText = Resources.Load<TextAsset>("Chapter1/chapter1");
            var modelsText = Resources.Load<TextAsset>("Jigsaw/models");
            Models = ModelLibrary.Load(modelsText.text);
            Data = chapterText ? ChapterData.Parse(chapterText.text) : new ChapterData();
            Blue = Data.BlueWords;
            State = new GameState();

            foreach (var n in FindObjectsByType<NpcActor>(FindObjectsInactive.Include, FindObjectsSortMode.None)) if (!string.IsNullOrEmpty(n.npcId) && !npcs.ContainsKey(n.npcId)) npcs[n.npcId] = n;
            foreach (var p in FindObjectsByType<PuzzleObject>(FindObjectsInactive.Include, FindObjectsSortMode.None)) puzzles[p.puzzleId] = p;
            foreach (var it in FindObjectsByType<Interactable>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (it.kind == Interactable.Kind.Inscription) inscriptions[it.id] = it;

            PlaceZone.Entered += OnPlaceEnter;
            PlaceZone.Exited += OnPlaceExit;
            HookState();
        }

        void OnPlaceEnter(string p)
        {
            Fire("enter:" + p);
            // 음악은 사건(["music", …])과 장면이 바꿈 — 장소를 넘을 때마다 되돌리지 않음(데이터 담당 요청 10/23)
            if (ui && ui.Bound && !Busy && Data.Places.TryGetValue(p, out var pd)) ui.ShowPlaceName(pd.Name);
        }

        void OnPlaceExit(string p) => Fire("leave:" + p);

        void HookState()
        {
            State.Changed += OnStateChanged;
            State.FlagSet += f => { if (!f.StartsWith("ev:") && !f.StartsWith("prop:")) Fire("flag:" + f); };
            State.WordConfirmed += w => { AudioHub.Play("confirm", 0.6f); ui?.Toast("글자 확정", w, true); };
            State.WordSeen += OnWordSeen;
        }

        void OnDestroy() { PlaceZone.Entered -= OnPlaceEnter; PlaceZone.Exited -= OnPlaceExit; if (I == this) I = null; }

        void Start()
        {
            if (followCamera) { followCamera.target = player.transform; followCamera.SnapToTarget(); }
            foreach (var p in Data.Props.Values) SetProp(p.Id, p.Initial, animate: false, remember: false);
            // 4-3 손 끌어당기기(pz_pull): 누를 자리를 키노피오 손에 붙여 따라다니게(QA P0-3 — 고정 자리면 안 보이고 엇나감)
            if (PropState.All.TryGetValue("kid_hand", out var kh) && npcs.TryGetValue("kinopio", out var kidA))
            {
                Transform hand = null;
                foreach (var tr in kidA.GetComponentsInChildren<Transform>(true)) if (tr.name == "HandL" || tr.name.EndsWith("_HandL")) { hand = tr; break; }
                kh.transform.SetParent(hand ? hand : kidA.transform, false);
                kh.transform.localPosition = hand ? Vector3.zero : new Vector3(0.25f, 0.55f, 0.2f);
            }
            ui.ShowTitle(GameState.HasSave, NewGame, ContinueGame);
            AudioHub.Music("music_title");
        }

        public void NewGame()
        {
            AudioHub.Music("music_village2");
            GameState.DeleteSave();
            State = new GameState();
            HookState();
            ui.Bind(this);
            StartCoroutine(BeginRoutine());
        }

        public void ContinueGame()
        {
            AudioHub.Music("music_village2");
            if (!State.Load()) { NewGame(); return; }
            ui.Bind(this);
            if (State.SavedPlayerPosition.HasValue)
            {
                player.Warp(State.SavedPlayerPosition.Value);
                var ar = AreaSystem.I;   // 이어하기: 저장한 자리의 구역을 켬(안 그러면 땅이 안 그려지고 클릭도 안 됨 — QA P0-1)
                if (ar != null && ar.isActiveAndEnabled) ar.SetActive(ar.Of(State.SavedPlayerPosition.Value), snap: true);
            }
            foreach (var f in State.Flags.Where(f => f.StartsWith("prop:")).ToList())
            {
                var parts = f.Split(':');
                if (parts.Length == 3) SetProp(parts[1], parts[2], animate: false, remember: false);
            }
            foreach (var p in puzzles.Values) p.Reapply(State);
            if (State.Has("f_kid_follow") && npcs.TryGetValue("kinopio", out var kid)) kid.Follow(player.transform);
            currentPhase = null;
            foreach (var pl in Data.Plays.Values)
                if (J.Bool(pl.Raw, "loop", false) && pl.Raw.TryGetValue("when", out var pw) && Condition.From(pw).Eval(State)) StartCoroutine(PlayControl(pl.Id, "start"));
            OnStateChanged();
            followCamera.SnapToTarget();
            StartCoroutine(ui.FadeIn(1f));
            Fire("load");
        }

        IEnumerator BeginRoutine()
        {
            yield return null;
            Fire("start");
        }

        // ── 입력 ──────────────────────────────────────────
        void Update()
        {
            if (ui == null || !ui.Bound) return;
            if (savePending && !runningEvents && !Busy) { savePending = false; Save(); }
            BusyWatchdog();
            if (!Typing() && !ui.TypingText && (Input.GetKeyDown(KeyCode.Tab) || Input.GetKeyDown(KeyCode.J))) ui.ToggleJournal();
            if (Input.GetKeyDown(KeyCode.Escape)) ui.Escape();
            TrackZones();
            if (Busy || ui.BlocksWorld || player == null) { SetHover(null); return; }

            var cam = Camera.main;
            if (!cam) return;
            var ray = cam.ScreenPointToRay(Input.mousePosition);
            Interactable hit = null;
            if (!ui.PointerOverUI && PointerRay(ray, out var info))
            {
                hit = info.collider.GetComponentInParent<Interactable>();
                if (hit && !hit.available) hit = null;
                if (PickMode && hit && hit.kind != Interactable.Kind.Npc) hit = null;
                var areas = AreaSystem.I;
                var nearExit = hit == null && areas != null ? areas.ExitNear(info.point) : null;
                ui.SetExitHover(nearExit != null ? (Data.Areas.TryGetValue(nearExit.To, out var ta) ? ta.Name : nearExit.Label) : null);
                if (Input.GetMouseButtonDown(0))
                {
                    if (PickMode) { if (hit) StartCoroutine(Pick(hit.id)); }
                    else if (hit) Approach(hit);
                    else player.WalkTo(areas != null ? areas.ResolveClick(info.point, out _) : info.point);
                }
            }
            else ui.SetExitHover(null);
            SetHover(hit);
            if (Input.GetMouseButtonDown(2)) RevealNearby();   // 휠 클릭: 둘레 살피기(화-03)
        }

        readonly Dictionary<string, Vector3> leadFinal = new Dictionary<string, Vector3>();
        /// <summary>앞장서기를 지금 구역 기준으로 다시 냄(목적지가 다른 구역이면 그쪽 출구까지). 구역을 넘어간 뒤에도 부름.</summary>
        public void Relead(NpcActor n)
        {
            if (!n || !leadFinal.TryGetValue(n.npcId, out var final)) return;
            var id = n.npcId; var dest = final;
            var areas = AreaSystem.I;
            var ex = areas != null ? areas.ExitToward(final) : null;
            if (ex != null) dest = Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y));
            n.Lead(dest, player.transform, ex != null ? (System.Action)null : () => { leadFinal.Remove(id); Fire("arrive:" + id); });
        }

        static readonly RaycastHit[] rayHits = new RaycastHit[24];
        /// <summary>
        /// 마우스 광선: 눈에 안 보이는 것(구역 밖 벽·투명 막·꺼진 그림)은 건너뛰고 화면에 보이는 첫 표면을 고른다.
        /// 누를 수 있는 것은 0.6m 안쪽으로 가려져 있어도 잡아 준다(작은 물건이 바닥 장식에 묻히지 않게).
        /// </summary>
        bool PointerRay(Ray ray, out RaycastHit best)
        {
            best = default;
            int n = Physics.RaycastNonAlloc(ray, rayHits, 250f, ~0, QueryTriggerInteraction.Ignore);
            System.Array.Sort(rayHits, 0, n, Comparer<RaycastHit>.Create((x, y) => x.distance.CompareTo(y.distance)));
            bool found = false;
            for (int i = 0; i < n; i++)
            {
                var h = rayHits[i];
                var it = h.collider.GetComponentInParent<Interactable>();
                if (it && it.available && it.gameObject.activeInHierarchy) { if (!found || h.distance - best.distance < 0.6f) { best = h; return true; } }
                if (found) { if (h.distance - best.distance > 0.6f) break; continue; }
                if (!SeenSurface(h.collider)) continue;
                best = h; found = true;
            }
            return found;
        }

        static bool SeenSurface(Collider c)
        {
            if (c.GetComponentInParent<Interactable>()) return true;
            var r = c.GetComponent<Renderer>() ?? c.GetComponentInParent<Renderer>();
            return r != null && r.enabled && !r.forceRenderingOff && r.gameObject.activeInHierarchy;
        }

        /// <summary>지금 구역에서 누를 수 있는 것마다 잉크 동그라미+아이콘(UI)과 반짝임. 출구도 함께.</summary>
        void RevealNearby()
        {
            var items = new List<(Vector3, CursorKind, string)>();
            var areas = AreaSystem.I;
            foreach (var it in Interactable.All)
            {
                if (!it.available || !it.gameObject.activeInHierarchy) continue;
                if (areas != null && areas.isActiveAndEnabled ? !areas.InActive(it.transform.position) : Vector3.Distance(it.transform.position, player.transform.position) > 22f) continue;
                it.Pulse(2.2f);
                var pos = it.kind == Interactable.Kind.Npc && npcs.TryGetValue(it.id, out var na) ? na.HeadPosition + Vector3.up * 0.3f : it.transform.position + Vector3.up * 0.6f;
                items.Add((pos, it.kind == Interactable.Kind.Npc ? CursorKind.Talk : it.kind == Interactable.Kind.Puzzle ? CursorKind.Use : CursorKind.Default, Label(it)));
            }
            if (areas != null && areas.Def(areas.Active) is AreaDef ad)
                foreach (var e in ad.Exits)
                    items.Add((Ground(new Vector3(e.Pos.x, 0, e.Pos.y)) + Vector3.up * 0.8f, CursorKind.Walk, Data.Areas.TryGetValue(e.To, out var ta) ? ta.Name : e.Label));
            ui.ShowInteractMarkers(items, 2.6f);
            AudioHub.Play("page", 0.25f, 1.6f);
        }

        bool Typing()
        {
            var doc = ui.GetComponent<UnityEngine.UIElements.UIDocument>();
            var fe = doc != null && doc.rootVisualElement.panel != null ? doc.rootVisualElement.panel.focusController.focusedElement as UnityEngine.UIElements.VisualElement : null;
            return fe != null && (fe is UnityEngine.UIElements.TextField || fe.GetFirstAncestorOfType<UnityEngine.UIElements.TextField>() != null);
        }

        /// <summary>구역(zones) 출입과 크리처 가까이 감(near:) 알림.</summary>
        void TrackZones()
        {
            if (!player) return;
            var p = new Vector2(player.transform.position.x, player.transform.position.z);
            foreach (var z in Data.Zones.Values)
            {
                bool inside = (p - z.Pos).sqrMagnitude <= z.Radius * z.Radius;
                if (inside && insideZones.Add(z.Id)) Fire("enter:" + z.Id);
                else if (!inside && insideZones.Remove(z.Id)) Fire("leave:" + z.Id);
            }
            foreach (var kv in npcs)
            {
                if (!kv.Value || !kv.Value.gameObject.activeInHierarchy) continue;
                bool near = Vector3.Distance(kv.Value.transform.position, player.transform.position) < 3.6f;
                if (near && nearNpcs.Add(kv.Key)) Fire("near:" + kv.Key);
                else if (!near) nearNpcs.Remove(kv.Key);
            }
        }

        void SetHover(Interactable it)
        {
            if (hovered == it) return;
            if (hovered) hovered.SetHover(false);
            hovered = it;
            if (hovered) hovered.SetHover(true);
            ui?.SetCursor(it == null ? CursorKind.Default : it.kind == Interactable.Kind.Npc ? CursorKind.Talk : CursorKind.Use, it ? Label(it) : null);
        }

        string Label(Interactable it)
        {
            if (PickMode) return "짚기";
            if (!string.IsNullOrEmpty(it.hoverLabel)) return it.hoverLabel;
            if (it.kind == Interactable.Kind.Npc && Data.Npcs.TryGetValue(it.id, out var n)) return n.Name;
            if (it.kind == Interactable.Kind.Inscription && Data.Inscriptions.TryGetValue(it.id, out var ins)) return ins.Label;
            if (it.kind == Interactable.Kind.Item && Data.Readables.TryGetValue(it.id, out var rd)) return rd.Label;
            return null;
        }

        void Approach(Interactable it)
        {
            var target = it.ApproachPoint(player.transform.position);
            player.WalkTo(target, () => { if (Busy || ui.BlocksWorld) return; player.Face(it.transform.position); Interact(it); }, it.transform.position);
        }

        public void Interact(Interactable it)
        {
            switch (it.kind)
            {
                case Interactable.Kind.Npc:
                    var dl = OpenDialogueFor(it.id);
                    if (dl != null) StartDialogue(dl);
                    else
                    {
                        bool handled = Data.Events.Any(e => Matches(e.On, "talk:" + it.id) && e.When.Eval(State) && !(e.Once && State.Has("ev:" + e.Id)));
                        Fire("talk:" + it.id);
                        if (!handled && npcs.TryGetValue(it.id, out var a) && !a.Following) StartCoroutine(director.React(it.id, "glance"));
                    }
                    break;
                case Interactable.Kind.Inscription:
                    Fire("touch:" + it.id);
                    if (Data.Inscriptions.TryGetValue(it.id, out var ins)) ui.OpenInscription(ins);
                    break;
                case Interactable.Kind.Puzzle:
                    if (puzzles.TryGetValue(it.id, out var pz)) pz.Use();
                    break;
                case Interactable.Kind.Item:
                    if (Data.Readables.TryGetValue(it.id, out var rd)) { ui.OpenReadable(rd); Fire("read:" + rd.Id); }
                    else Fire("touch:" + it.id);
                    break;
                default:
                    Fire("touch:" + it.id);
                    break;
            }
        }

        public DialogueDef OpenDialogueFor(string npcId) =>
            Data.Dialogues.Values.FirstOrDefault(d => d.Npc == npcId && !State.Has("done:" + d.Id) && d.OpensWhen.Eval(State));

        public void StartDialogue(DialogueDef d)
        {
            Busy = true;
            player.Stop();
            if (npcs.TryGetValue(d.Npc, out var a))
            {
                a.LookAt(player.transform.position);
                player.Face(a.transform.position);
                followCamera?.Focus(Vector3.Lerp(player.transform.position, a.transform.position, 0.5f), new FollowCamera.View { yaw = followCamera.CurrentYaw, pitch = 28, distance = 11, fov = 30, offset = new Vector3(0, 1.8f, 0) });
            }
            ui.OpenDialogue(d, OnDialogueClosed);
        }

        void OnDialogueClosed(DialogueDef d, bool success)
        {
            followCamera?.Focus(null);
            Busy = false;
            if (success) { State.Set("tut_board"); Fire("done:" + d.Id); State.Set("done:" + d.Id); }   // 첫 대화를 마치면 조립판 안내 쪽지는 끝
            Save();
        }

        /// <summary>대화 응답 하나를 실행: 깃발, 상대 반응, 곁의 반응(also), 대답(say). 진행 응답이면 쓴 글자에 “써서 통함”.</summary>
        public IEnumerator RunResponse(DialogueDef d, ResponseDef r, IReadOnlyList<string> usedWords, bool counted)
        {
            if (r == null) yield break;
            if (r.Progress || J.Bool(r.Raw, "understood", false))
                foreach (var w in usedWords) State.MarkUsed(w, Data.IsGuessCorrect);
            foreach (var f in r.Set) State.Set(f);
            var running = new List<Coroutine>();
            if (r.Raw != null && r.Raw.TryGetValue("also", out var also) && also is List<object> al)
                foreach (var x in al.OfType<List<object>>())
                    if (x.Count >= 2) running.Add(StartCoroutine(director.React(x[0]?.ToString(), x[1]?.ToString())));
            if (!string.IsNullOrEmpty(r.Say) && npcs.TryGetValue(d.Npc, out var n)) ui.ShowOverhead(n, r.Say, 5f);
            if (!string.IsNullOrEmpty(r.React)) yield return director.React(d.Npc, r.React);
            foreach (var c in running) yield return c;

            if (!r.Progress && counted)
            {
                dialogueFails.TryGetValue(d.Id, out var fails); fails++; dialogueFails[d.Id] = fails;
                foreach (var nd in J.List(d.Raw, "nudges").OfType<Dictionary<string, object>>())
                {
                    if ((int)J.F(nd.TryGetValue("afterFails", out var af) ? af : 99) != fails) continue;
                    var who = J.Str(nd, "npc", d.Npc);
                    var say = J.Str(nd, "say");
                    if (!string.IsNullOrEmpty(say) && npcs.TryGetValue(who, out var wn)) ui.ShowOverhead(wn, say, 6f);
                    yield return director.React(who, J.Str(nd, "react"));
                }
            }
        }

        void DevPick(string npcId) { StartCoroutine(Pick(npcId)); }

        // ── 짚기(5-4) ────────────────────────────────────
        public void BeginPick()
        {
            PickMode = true; ui.SetPickPrompt(true);
            var pick = Data.Puzzles.Values.FirstOrDefault(p => p.Type == "pick");
            var zone = pick != null ? J.Str(pick.Raw, "zone") : null;
            var focus = !string.IsNullOrEmpty(zone) && Data.Zones.ContainsKey(zone) ? At(zone) : Vector3.Lerp(At("z_crowd_rows"), At("z_back_corner"), 0.35f);
            followCamera?.Focus(focus, new FollowCamera.View { yaw = followCamera.CurrentYaw, pitch = 34, distance = 15, fov = 36, offset = new Vector3(0, 0.6f, 0) });
        }

        IEnumerator Pick(string npcId)
        {
            var pz = Data.Puzzles.Values.FirstOrDefault(p => p.Type == "pick");
            if (pz == null) yield break;
            string target = J.Str(pz.Raw, "target", "kinopio");
            AudioHub.Play("piece", 0.6f);
            if (npcId == target)
            {
                PickMode = false; ui.SetPickPrompt(false); followCamera?.Focus(null);
                player.GetComponentInChildren<ProceduralRig>()?.SetPose(ProceduralRig.Pose.Stand);
                foreach (var f in pz.Set) State.Set(f);
                State.Set("puzzle:" + pz.Id);
                Fire("puzzle:" + pz.Id);
                Save();
            }
            else yield return director.React(npcId, J.Str(pz.Raw, "wrongReact", "villager_lift_head"));
        }

        // ── 사건 ──────────────────────────────────────────
        public void Fire(string trigger)
        {
            pendingTriggers.Enqueue(trigger);
            if (!runningEvents) StartCoroutine(RunEvents());
        }

        IEnumerator RunEvents()
        {
            runningEvents = true;
            while (pendingTriggers.Count > 0)
            {
                var trig = pendingTriggers.Dequeue();
                foreach (var e in Data.Events.ToList())
                {
                    if (!Matches(e.On, trig)) continue;
                    if (e.Once && State.Has("ev:" + e.Id)) continue;
                    if (!e.When.Eval(State)) continue;
                    if (e.Once) State.Set("ev:" + e.Id);
                    foreach (var a in e.Do) yield return Guard(Do(a));
                }
            }
            runningEvents = false;
            OnStateChanged();
        }

        /// <summary>동작 하나에서 예외가 나도 사슬과 입력이 잠기지 않게(QA P1-7).</summary>
        public static IEnumerator Guard(IEnumerator e)
        {
            while (true)
            {
                object cur;
                try { if (!e.MoveNext()) yield break; cur = e.Current; }
                catch (Exception ex) { Debug.LogException(ex); yield break; }
                if (cur is IEnumerator nested) yield return Guard(nested); else yield return cur;
            }
        }

        /// <summary>id 그대로 또는 무리(id_2, id_3 …).</summary>
        public IEnumerable<NpcActor> Group(string id)
        {
            foreach (var kv in npcs) if (kv.Key == id || kv.Key.StartsWith(id + "_") && char.IsDigit(kv.Key[kv.Key.Length - 1])) yield return kv.Value;
        }

        static bool Matches(string on, string trig)
        {
            if (string.IsNullOrEmpty(on)) return false;
            foreach (var part in on.Split('|')) if (part.Trim() == trig) return true;
            return false;
        }

        IEnumerator Do(List<object> a)
        {
            if (a.Count == 0) yield break;
            string op = a[0]?.ToString();
            string A(int i) => a.Count > i ? a[i]?.ToString() : null;
            switch (op)
            {
                case "set": State.Set(A(1)); break;
                case "unset": case "clear": State.Unset(A(1)); if (A(1) == "f_kid_follow" && npcs.TryGetValue("kinopio", out var k0) && k0.Following) k0.StopFollow(); break;
                case "goal": OnStateChanged(); break;
                case "save": Save(); break;
                case "wait": yield return new WaitForSeconds(J.F(a.Count > 1 ? a[1] : 1)); break;
                case "see": State.See(A(1), PlaceZone.Current); break;
                case "toast": ui.Toast(A(1), A(2), false); break;
                case "thought": ui.ShowThought(A(1), a.Count > 2 ? J.F(a[2]) : 3.5f); break;
                case "decree":   // 왕의 띠를 손으로 벗겨 밑의 사람 글을 읽음(UI 띠 벗기기). 다 벗기면 decree:<band> 깃발
                {
                    var band = A(1) ?? "decree_band"; var human = A(2) ?? "decree_human";
                    yield return ui.ShowDecree(band, human);
                    if (ui.DecreePeeled) { State.Set("decree:" + band); Fire("decree:" + band); }
                    break;
                }
                case "sound": AudioHub.Play(A(1), a.Count > 2 ? J.F(a[2]) : 0.7f, a.Count > 3 ? J.F(a[3]) : 1f); break;   // ["sound", 이름, 음량?, 높낮이?]
                case "music": AudioHub.Music(A(1) ?? ""); break;                                                            // ["music", "music_truth"] / ["music", ""] = 끔
                case "loop": AudioHub.Loop(A(1), A(2), a.Count > 3 ? J.F(a[3]) : 0.5f); break;                             // ["loop", 열쇠, 이름, 음량?]
                case "stoploop": AudioHub.StopLoop(A(1)); break;
                case "gesture":   // 다음 대화에 몸짓 쪽지(self/other/both)
                    ui.ShowGestureHint(A(1) ?? "both");
                    break;
                case "clip":   // ["clip", npc|hero, 클립 이름] — 자세 표에 없는 블렌더 클립을 한 번
                {
                    var who = A(1);
                    var r = who == "hero" || who == "player" ? player.GetComponentInChildren<ProceduralRig>() : (npcs.TryGetValue(who ?? "", out var cn) ? cn.Rig : null);
                    float len = r ? r.PlayClip(A(2)) : 0f;
                    if (a.Count > 3 && A(3) == "wait" && len > 0) yield return new WaitForSeconds(len);
                    break;
                }
                case "read":   // 사람 글 화면을 열고 닫힐 때까지 기다림
                    if (Data.Readables.TryGetValue(A(1), out var rdx)) { ui.OpenReadable(rdx); Fire("read:" + rdx.Id); while (ui.BlocksWorld) yield return null; }
                    break;
                case "companion":
                    if (npcs.TryGetValue(A(1), out var c))
                    {
                        bool on = a.Count > 2 && a[2] is bool b ? b : A(2) == "true";
                        if (on) { c.Follow(player.transform); State.Set("f_kid_follow"); } else { c.StopFollow(); }
                    }
                    break;
                case "npc":
                    if (npcs.TryGetValue(A(1), out var n)) yield return NpcAction(n, A(2), a);
                    break;
                case "hero":
                    yield return director.HeroAction(A(1), A(2), a);
                    break;
                case "prop": SetProp(A(1), A(2), animate: true); break;
                case "board":
                    State.Set("f_board_open");
                    ui.Toast("말하는 판이 열렸다", "모형을 판에 놓고 글자를 넣어 말한다.", false);
                    break;
                case "glint":
                    foreach (var it in Interactable.All.Where(x => x.id == A(1))) it.Pulse(4f);
                    AudioHub.Play("almost", 0.4f, 1.5f);
                    break;
                case "scene":
                    Busy = true;
                    yield return director.Play(A(1));
                    Busy = false;
                    Fire("sceneEnd:" + A(1));
                    break;
                case "react":
                    yield return director.React(A(1), A(2));
                    break;
                case "play":
                    yield return PlayControl(A(1), A(2) ?? "start");
                    break;
                case "puzzle":
                    if (puzzles.TryGetValue(A(1), out var pz)) pz.SetState(A(2));
                    break;
                case "pick": BeginPick(); break;
                case "enable":
                case "disable":
                    foreach (var it in Interactable.All.Where(x => x.id == A(1)).ToList()) it.SetAvailable(op == "enable");
                    break;
                case "dialogue":
                    if (Data.Dialogues.TryGetValue(A(1), out var dl)) { StartDialogue(dl); while (ui.BlocksWorld) yield return null; }
                    break;
                case "chapterEnd":
                case "end":
                    Busy = true;
                    GameState.DeleteSave();
                    ui.ShowEnding();
                    break;
                default:
                    Debug.LogWarning($"[OUAT] 모르는 행동: {op}");
                    break;
            }
        }

        IEnumerator NpcAction(NpcActor n, string what, List<object> a)
        {
            string A(int i) => a.Count > i ? a[i]?.ToString() : null;
            switch (what)
            {
                case "pose": director.ApplyPose(n, A(3)); break;
                case "react": yield return director.React(n.npcId, A(3)); break;
                case "look": n.LookAt(At(a.Count > 3 ? a[3] : "player")); break;
                case "move": case "moveTo": case "walk":
                {
                    bool wait = a.Count > 4 && A(4) == "wait";
                    var target = At(a.Count > 3 ? a[3] : null);
                    bool done = false;
                    n.WalkTo(target, () => done = true);
                    if (wait) { float t = 0; while (!done && t < 25f) { t += Time.deltaTime; yield return null; } }
                    break;
                }
                case "warp": n.Warp(At(a.Count > 3 ? a[3] : null)); break;
                case "lead":   // 앞장서기: 주인공을 기다려 가며 그 자리까지 → 둘 다 닿으면 arrive:<npc>
                    leadFinal[n.npcId] = At(a.Count > 3 ? a[3] : null);
                    Relead(n);
                    break;
                case "follow": n.Follow(player.transform); break;
                case "stay": n.StopFollow(); break;
                case "hide": n.gameObject.SetActive(false); break;
                case "show": n.gameObject.SetActive(true); break;
                case "say":
                    if (Data.Sentences.ContainsKey(A(3) ?? "")) ui.ShowOverhead(n, A(3), a.Count > 4 ? J.F(a[4]) : 5f);
                    break;
            }
        }

        IEnumerator PlayControl(string id, string mode)
        {
            if (!Data.Plays.TryGetValue(id ?? "", out var play)) yield break;
            bool loop = J.Bool(play.Raw, "loop", false);
            if (mode == "stop") { if (rehearsal != null) StopCoroutine(rehearsal); rehearsal = null; director.EndPlay(); yield break; }
            if (loop)
            {
                if (rehearsal != null) StopCoroutine(rehearsal);
                rehearsal = StartCoroutine(director.PlayLoop(play));
                yield break;
            }
            if (rehearsal != null) { StopCoroutine(rehearsal); rehearsal = null; }
            Busy = true;
            yield return director.PlayOnce(play);
            Busy = false;
            Fire("playEnd:" + id);
        }

        // ── 자리 풀이: 구역 id / 장소 id / [x,z] / 크리처 id / "player" ──
        public Vector3 At(object target)
        {
            if (target is Vector3 v3) return Ground(v3);
            if (target is List<object> l && l.Count >= 2) return Ground(new Vector3(J.F(l[0]), 0, J.F(l[1])));
            var s = target?.ToString();
            if (string.IsNullOrEmpty(s) || s == "player" || s == "hero") return player.transform.position;
            if (Data.Zones.TryGetValue(s, out var z)) return Ground(new Vector3(z.Pos.x, 0, z.Pos.y));
            if (Data.Places.TryGetValue(s, out var _)) return Ground(PlaceCenter(s));
            if (npcs.TryGetValue(s, out var n)) return n.transform.position;
            if (PropState.All.TryGetValue(s, out var pr)) return pr.transform.position;
            if (Data.Inscriptions.TryGetValue(s, out var ins)) return Ground(new Vector3(ins.Pos.x, 0, ins.Pos.y));
            return player.transform.position;
        }

        public Vector3 ZonePoint(string zoneId) => At(zoneId);

        public static Vector3 Ground(Vector3 p)
        {
            if (Physics.Raycast(new Vector3(p.x, 40f, p.z), Vector3.down, out var hit, 80f, ~0, QueryTriggerInteraction.Ignore)) return hit.point;
            return p;
        }

        public Vector3 PlaceCenter(string id)
        {
            foreach (var z in FindObjectsByType<PlaceZone>(FindObjectsSortMode.None)) if (z.placeId == id) return z.transform.position;
            if (Data.Places.TryGetValue(id ?? "", out var p) && p.Raw != null)
            {
                var c = J.List(p.Raw, "center");
                if (c.Count >= 2) return new Vector3(J.F(c[0]), 0, J.F(c[1]));
            }
            return player.transform.position;
        }

        public NpcActor Npc(string id) => npcs.TryGetValue(id ?? "", out var n) ? n : null;
        public IEnumerable<NpcActor> AllNpcs => npcs.Values;
        public PuzzleObject Puzzle(string id) => puzzles.TryGetValue(id ?? "", out var p) ? p : null;

        public void SetProp(string id, string state, bool animate = true, bool remember = true)
        {
            if (string.IsNullOrEmpty(id)) return;
            if (remember)
            {
                foreach (var f in State.Flags.Where(f => f.StartsWith("prop:" + id + ":")).ToList()) State.Unset(f);
                State.Set("prop:" + id + ":" + state);
            }
            if (PropState.All.TryGetValue(id, out var p)) p.Set(state, animate);
        }

        // ── 상태가 바뀔 때: 단계 배치, 머리 위 말, 목표, 퍼즐·읽을거리 열림 ──
        void OnStateChanged()
        {
            if (Data == null || ui == null || !ui.Bound) return;
            var phase = Data.CurrentPhase(State);
            if (phase != null && phase.Id != currentPhase && !runningEvents && !Busy && !ui.BlocksWorld) { currentPhase = phase.Id; StartCoroutine(ApplyPhase(phase)); }

            foreach (var kv in npcs)
            {
                var oh = Data.Overheads.LastOrDefault(o => o.Npc == kv.Key && o.When.Eval(State));
                ui.SetPersistentOverhead(kv.Value, oh?.Sentence);
                var it = kv.Value.GetComponent<Interactable>();
                if (it && Data.Npcs.TryGetValue(kv.Key, out var nd))
                    it.hoverLabel = OpenDialogueFor(kv.Key) != null ? nd.Name + " · 말 걸기" : nd.Name;
            }
            foreach (var kv in inscriptions)
                if (State.InscriptionRead(kv.Key)) ui.MarkInscriptionRead(kv.Value, kv.Key);
            foreach (var p in puzzles.Values)
                if (Data.Puzzles.TryGetValue(p.puzzleId, out var pd))
                {
                    bool open = !p.Solved && (pd.Raw == null || !pd.Raw.ContainsKey("opensWhen") || Condition.From(pd.Raw["opensWhen"]).Eval(State)) && !J.Bool(pd.Raw, "auto", false);
                    if (J.Bool(pd.Raw, "repeatable", false)) open = Condition.From(pd.Raw.TryGetValue("opensWhen", out var ow) ? ow : null).Eval(State);
                    // 누르는 자리(Use_<id>)는 장치의 자식에 붙어 있다 — 부모만 찾으면 영영 못 누름(사다리 버그)
                    var it = p.GetComponentInChildren<Interactable>(true);
                    if (it && pd.Type != "pick") it.SetAvailable(open);
                }
            var pick = Data.Puzzles.Values.FirstOrDefault(p => p.Type == "pick");
            if (pick != null && !PickMode && !State.Has("puzzle:" + pick.Id) && pick.Raw.TryGetValue("opensWhen", out var pow) && Condition.From(pow).Eval(State)) BeginPick();
            foreach (var rd in Data.Readables.Values)
            {
                bool vis = rd.VisibleWhen.Eval(State);
                foreach (var it in Interactable.All.Where(x => x.id == rd.Id)) it.SetAvailable(vis);
            }
            var goal = Data.CurrentGoal(State);
            ui.SetGoal(goal?.Text, goal != null && Data.Places.TryGetValue(goal.Place ?? "", out var gp) ? gp.GoalName : null, goal?.Hint);
            StateRefreshed?.Invoke();
        }

        IEnumerator ApplyPhase(PhaseDef phase)
        {
            var cam = Camera.main;
            foreach (var kv in phase.Npcs)
            {
                if (kv.Value.When != null && !kv.Value.When.Eval(State)) continue;
                foreach (var n in Group(kv.Key))
                {
                    yield return PlaceNpc(n, kv.Value, cam);
                }
            }
        }

        IEnumerator PlaceNpc(NpcActor n, PhaseNpc pv, Camera cam)
        {
            {
                var kv = new KeyValuePair<string, PhaseNpc>(n.npcId, pv);
                bool member = n.npcId.Contains("_") && char.IsDigit(n.npcId[n.npcId.Length - 1]) && Data.Npcs.ContainsKey(n.npcId.Substring(0, n.npcId.LastIndexOf('_')));   // count>1 무리(crowd·collectors 등)는 모두 펼침
                var at = kv.Value.At?.ToString();
                if (at == "companion" || at == "follow") { n.Follow(player.transform); director.ApplyPose(n, "stand"); yield break; }
                if (at == "lead") { director.ApplyPose(n, "stand"); yield break; }
                if (n.Following && State.Has("f_kid_follow")) yield break;
                var target = At(kv.Value.At);
                if (member) { int k = n.npcId[n.npcId.Length - 1] - '0'; target += new Vector3(Mathf.Cos(k * 2.1f), 0, Mathf.Sin(k * 2.1f)) * (1.2f + k * 0.35f); }
                var ar = AreaSystem.I;
                bool visible = ar != null ? (ar.InActive(n.transform.position) || ar.InActive(target)) && (IsVisible(cam, n.transform.position) || IsVisible(cam, target)) : (cam && IsVisible(cam, n.transform.position) || IsVisible(cam, target));
                if (Vector3.Distance(n.transform.position, target) > 0.6f)
                {
                    if (visible && Vector3.Distance(n.transform.position, target) < 30f) n.WalkTo(target, () => director.ApplyPose(n, kv.Value.Pose));
                    else { n.Warp(target); director.ApplyPose(n, kv.Value.Pose); }
                }
                else director.ApplyPose(n, kv.Value.Pose);
                yield return null;
            }
        }

        static bool IsVisible(Camera cam, Vector3 p)
        {
            if (!cam) return false;
            var v = cam.WorldToViewportPoint(p);
            return v.z > 0 && v.x > -0.1f && v.x < 1.1f && v.y > -0.1f && v.y < 1.1f;
        }

        bool savePending;
        /// <summary>사건 사슬·장면 도중에는 미루고(QA P0-2), 끝난 뒤 저장한다.</summary>
        public void Save()
        {
            if (runningEvents || Busy) { savePending = true; return; }
            State.Save(player ? player.transform.position : (Vector3?)null);
        }

        // ── 낱말을 본 자리(기록장 “마지막으로 본 자리”): 낱말이 처음/다시 보일 때 화면을 한 장 잘라 UI에 넘김 ──
        readonly Dictionary<string, float> lastSighting = new Dictionary<string, float>();
        void OnWordSeen(string word)
        {
            if (!isActiveAndEnabled || ui == null || ui.BlocksWorld) return;
            if (lastSighting.TryGetValue(word, out var t0) && Time.time - t0 < 30f) return;
            lastSighting[word] = Time.time;
            StartCoroutine(CaptureSighting(word));
        }
        System.Collections.IEnumerator CaptureSighting(string word)
        {
            yield return new WaitForEndOfFrame();
            var full = ScreenCapture.CaptureScreenshotAsTexture();
            if (!full) yield break;
            int w = Mathf.Min(full.width, Mathf.RoundToInt(full.height * 0.62f)), h = Mathf.RoundToInt(w * 0.69f);
            var cam = Camera.main; var c = new Vector2(full.width / 2f, full.height / 2f);
            if (cam && player) { var sp = cam.WorldToScreenPoint(player.transform.position + Vector3.up); c = new Vector2(sp.x, sp.y); }
            int x = Mathf.Clamp(Mathf.RoundToInt(c.x - w / 2f), 0, full.width - w), y = Mathf.Clamp(Mathf.RoundToInt(c.y - h / 2f), 0, full.height - h);
            var crop = new Texture2D(320, 220, TextureFormat.RGB24, false);
            var px = full.GetPixels(x, y, w, h);
            var src = new Texture2D(w, h, TextureFormat.RGB24, false); src.SetPixels(px); src.Apply();
            var rt = RenderTexture.GetTemporary(320, 220); Graphics.Blit(src, rt);
            var prev = RenderTexture.active; RenderTexture.active = rt; crop.ReadPixels(new Rect(0, 0, 320, 220), 0, 0); crop.Apply(); RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt); Destroy(src); Destroy(full);
            ui.RememberSighting(word, crop);
        }

        void OnApplicationQuit() { if (ui && ui.Bound && !State.Has("f_end") && !runningEvents && !Busy) Save(); }
    }
}
