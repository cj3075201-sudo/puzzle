using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using OUAT.World;
using UnityEngine;

namespace OUAT.Core
{
    /// <summary>
    /// 연출: 자세(pose)·반응(react)·장면(scene)·극(play). 이름은 docs/반응목록.md와 같다.
    /// 장면은 sc_* 메서드(DirectorScenes.cs), 반응은 이 파일의 표. 표에 없는 반응은 이름의 낱말로 자세를 고른다.
    /// </summary>
    public partial class Director : MonoBehaviour
    {
        public FishActor fish;
        public Transform lightShaft;
        public Transform stageCenter;

        Game G => Game.I;
        readonly Dictionary<string, Func<IEnumerator>> scenes = new Dictionary<string, Func<IEnumerator>>();

        void Awake()
        {
            foreach (var m in GetType().GetMethods(System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public))
                if (m.Name.StartsWith("sc_") && m.ReturnType == typeof(IEnumerator) && m.GetParameters().Length == 0)
                {
                    var mm = m;
                    scenes[m.Name] = () => (IEnumerator)mm.Invoke(this, null);
                }
        }

        // ── 장면 ─────────────────────────────────────────
        public IEnumerator Play(string id)
        {
            if (string.IsNullOrEmpty(id)) yield break;
            if (scenes.TryGetValue(id, out var f))
            {
                // 레터박스(조작을 뺏는 컷신)는 이야기의 큰 순간에만 — 나머지는 플레이 화면 그대로 짧게(세나르처럼)
                bool cinematic = G.Data.Scenes.TryGetValue(id, out var sd) && sd != null ? J.Bool(sd, "cinematic", false) : Cinematic.Contains(id);
                if (cinematic) G.ui.SetCinematic(true);
                yield return Game.Guard(f());
                EndShot();
                if (cinematic) G.ui.SetCinematic(false);
                yield break;
            }
            Debug.Log($"[OUAT] 전용 연출 없는 장면: {id}");
            yield return Wait(0.5f);
        }

        static readonly HashSet<string> Cinematic = new HashSet<string>
        {
            "sc_wake", "sc_first_meet", "sc_gate_greet", "sc_fish_takes_cart", "sc_day_proclaim", "sc_assemble", "sc_kid_chosen", "sc_pond_procession", "sc_ending_fish", "sc_chapter_card"
        };

        // ── 도구 ─────────────────────────────────────────
        protected NpcActor N(string id) => G.Npc(id);
        protected Transform Hero => G.player.transform;
        protected ProceduralRig HeroRig => G.player.GetComponentInChildren<ProceduralRig>();
        protected Vector3 At(object t) => G.At(t);
        protected static IEnumerator Wait(float s) { yield return new WaitForSeconds(s); }

        /// <summary>카메라를 한 지점으로(플레이어 조종 아님). yaw는 null이면 지금 각도 유지.</summary>
        protected void Shot(Vector3 focus, float pitch = 30f, float distance = 12f, float? yaw = null, float fov = 32f, float height = 0.8f)
        {
            G.followCamera.Focus(focus, new FollowCamera.View { yaw = yaw ?? G.followCamera.CurrentYaw, pitch = pitch, distance = distance, fov = fov, offset = new Vector3(0, height, 0) });
        }
        protected void EndShot() { if (G && G.followCamera) G.followCamera.Focus(null); }

        protected void Pose(string npc, string pose) { var n = N(npc); if (n) ApplyPose(n, pose); }
        protected void HeroPose(string pose) { var r = HeroRig; if (r) r.SetPose(ProceduralRig.Parse(pose)); }
        protected void Look(string npc, object target) { var n = N(npc); if (n) n.LookAt(At(target)); }
        protected void Say(string npc, string sentence, float seconds = 5f) { var n = N(npc); if (n) G.ui.ShowOverhead(n, sentence, seconds); }
        protected void Prop(string id, string state) => G.SetProp(id, state);

        protected IEnumerator Walk(string npc, object target, bool wait = true, float timeout = 20f)
        {
            var n = N(npc); if (!n) yield break;
            bool done = false;
            n.WalkTo(At(target), () => done = true);
            if (!wait) yield break;
            float t = 0; while (!done && t < timeout) { t += Time.deltaTime; yield return null; }
        }

        protected IEnumerator HeroWalk(object target, float timeout = 20f)
        {
            bool done = false;
            G.player.WalkTo(At(target), () => done = true);
            float t = 0; while (!done && t < timeout) { t += Time.deltaTime; yield return null; }
        }

        protected void HeroFace(object target) => G.player.Face(At(target));

        // ── 자세 ─────────────────────────────────────────
        public void ApplyPose(NpcActor n, string pose)
        {
            if (!n) return;
            switch (pose)
            {
                case "follow": n.Follow(G.player.transform); n.SetPose(ProceduralRig.Pose.Stand); return;
                case "face_lump": n.LookAt(At("z_lump")); break;
                case "face_pond": n.LookAt(At("pond")); break;
                case "watch": case "line_up": case "act": case "rehearse": n.LookAt(At("z_doll_seat")); break;
                case "gather": n.LookAt(At("fall")); break;
            }
            n.SetPose(ProceduralRig.Parse(pose));
        }

        // ── 반응 ─────────────────────────────────────────
        public IEnumerator React(string npcId, string react)
        {
            if (string.IsNullOrEmpty(react)) yield break;
            if (npcId == "hero" || npcId == "player") { yield return HeroReact(react); yield break; }
            var n = N(npcId);
            if (!n) yield break;
            var rig = n.Rig;
            var keep = rig ? rig.pose : ProceduralRig.Pose.Stand;
            // 말 걸 때마다 엎드리면 “맨날 인사만” 반복(사용자 10/23) — 엎드림은 그 크리처의 첫 한 번만, 다음부터는 쳐다보고 고개를 갸웃하고 하던 일로 돌아감
            if (BowLike(react) && !bowedOnce.Add(npcId)) react = "glance_curious";
            switch (react)
            {
                case "glance_curious":
                    n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(1.1f);
                    n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.6f); n.SetPose(keep == ProceduralRig.Pose.Prostrate ? ProceduralRig.Pose.Stand : keep); n.LookAt(null); break;
                // 키노피오
                case "kid_glance_chief":
                    n.LookAt(At("chief")); yield return Wait(0.7f); if (rig) rig.FlickerNose(); yield return Wait(0.4f); n.LookAt(Hero.position); break;
                case "kid_point_hero":
                    n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Point); yield return Wait(1.3f); n.SetPose(keep); break;
                case "kid_offer_item":
                    n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Reach); yield return Wait(1.6f); n.SetPose(ProceduralRig.Pose.Gather); yield return Wait(0.7f); n.SetPose(keep); break;
                case "kid_point_self":
                    Say(npcId, "s_out_body", 5f); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(1.2f); n.LookAt(Hero.position); n.SetPose(keep); break;
                case "kid_prostrate_only": case "kid_stay_prostrate":
                    n.SetPose(ProceduralRig.Pose.Prostrate); yield return Wait(1.2f); break;
                case "kid_nod_stay":
                    n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(1f); n.LookAt(At("gate")); yield return Wait(0.6f); n.SetPose(ProceduralRig.Pose.Prostrate); break;
                case "kid_tremble_stay":
                    n.SetPose(ProceduralRig.Pose.Cower); yield return Wait(1.4f); n.SetPose(ProceduralRig.Pose.Prostrate); break;
                case "kid_look_field_stay":
                    n.LookAt(At("field")); yield return Wait(1.8f); n.SetPose(ProceduralRig.Pose.Prostrate); break;
                case "kid_rise_follow":
                    n.SetPose(ProceduralRig.Pose.Stand); yield return Wait(0.8f); n.LookAt(Hero.position); n.Follow(Hero); break;
                case "kid_look":
                    n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.LookUp); yield return Wait(1f); n.SetPose(keep); break;
                case "kid_stuck_pedestal":
                    n.SetPose(ProceduralRig.Pose.Reach); yield return Wait(0.9f); n.SetPose(ProceduralRig.Pose.HalfProstrate); yield return Wait(0.8f); break;
                case "kid_shrink":
                    n.SetPose(ProceduralRig.Pose.Cower); n.WalkTo(n.transform.position - n.transform.forward * 0.8f); yield return Wait(1f); n.SetPose(keep); break;
                case "kid_stay_face_pond": case "kid_stay_edge":
                    n.LookAt(At("pond")); n.SetPose(ProceduralRig.Pose.FacePond); yield return Wait(1f); break;
                case "kid_answer_point_stage":
                    n.LookAt(Hero.position); Say(npcId, "s_fish_eat", 5f); yield return Wait(2.2f);
                    n.LookAt(At("z_stage")); n.SetPose(ProceduralRig.Pose.Point); yield return Wait(2.2f); n.SetPose(ProceduralRig.Pose.Stand); break;
                case "kid_point_stage":
                    n.LookAt(At("z_stage")); n.SetPose(ProceduralRig.Pose.Point); yield return Wait(1.6f); n.SetPose(keep); break;
                case "kid_step_back":
                    n.WalkTo(n.transform.position + (n.transform.position - At("z_pond_center")).normalized * 1.2f); yield return Wait(1f); break;
                case "kid_take_hand_step": yield return KidStepIn(n, null); break;
                case "kid_read_stone_step": yield return KidStepIn(n, "stone"); break;
                case "kid_grip_fragment_step": yield return KidStepIn(n, "grip"); break;
                case "kid_look_up_step": yield return KidStepIn(n, "up"); break;
                case "kid_step_in": yield return KidStepIn(n, null); break;
                case "kid_look_stone":
                    n.LookAt(At("z_pond_stone")); yield return Wait(0.4f);
                    foreach (var it in Interactable.All.Where(x => x.id == "ins_pond")) it.Pulse(3f);
                    yield return Wait(2f); break;

                // 촌장
                case "chief_kneel":
                    n.SetPose(ProceduralRig.Pose.Kneel); yield return Wait(0.45f); AudioHub.Play("drop", 0.9f, 0.65f); G.ui.Shake(0.25f); yield return Wait(1f); break;
                case "chief_stay_half": n.SetPose(ProceduralRig.Pose.HalfProstrate); yield return Wait(1f); break;
                case "chief_tilt": n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(1.8f); n.SetPose(keep); break;
                case "chief_doubt": n.SetPose(ProceduralRig.Pose.Stand); yield return Wait(0.7f); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(1f); n.SetPose(ProceduralRig.Pose.HalfProstrate); break;
                case "chief_startle":
                    n.WalkTo(n.transform.position - n.transform.forward * 1.5f); yield return Wait(0.5f); n.SetPose(ProceduralRig.Pose.Prostrate); AudioHub.Play("wrong", 0.5f, 0.8f); yield return Wait(1.2f); break;
                case "chief_gesture_offer":
                    n.LookAt(At("kinopio")); n.SetPose(ProceduralRig.Pose.Point); yield return Wait(1.3f); n.SetPose(keep); break;
                case "chief_bow": n.SetPose(ProceduralRig.Pose.HalfProstrate); yield return Wait(1.2f); n.SetPose(keep); break;
                case "chief_silent_stand": n.SetPose(ProceduralRig.Pose.Still); yield return Wait(1f); break;
                case "chief_touch_inscription":
                    n.LookAt(At("ins_stage")); n.SetPose(ProceduralRig.Pose.Point); Say(npcId, "s_choose", 7f); yield return Wait(2.2f); n.SetPose(ProceduralRig.Pose.Stand); break;
                case "chief_point_doll_seat":
                    n.LookAt(At("z_doll_seat")); n.SetPose(ProceduralRig.Pose.Point); yield return Wait(1.6f); n.SetPose(keep); break;
                case "chief_repeat":
                    Say(npcId, "s_choose", 5f); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(1.6f); n.SetPose(ProceduralRig.Pose.Stand); break;
                case "chief_bow_block": n.SetPose(ProceduralRig.Pose.Prostrate); yield return Wait(1f); break;
                case "chief_proclaim_day": yield return ChiefProclaim(n, false); break;
                case "chief_tap_stage_then_proclaim": yield return ChiefProclaim(n, true); break;

                // 어미·밭 주민·그 밖
                case "mother_bow": n.SetPose(ProceduralRig.Pose.Prostrate); yield return Wait(1.4f); n.SetPose(keep); break;
                case "mother_crouch": n.SetPose(ProceduralRig.Pose.Crouch); yield return Wait(1f); break;
                case "stacker_load": n.SetPose(ProceduralRig.Pose.LoadCart); yield return Wait(1.5f); break;
                case "stacker_load_eager": n.SetPose(ProceduralRig.Pose.LoadCart); yield return Wait(1.2f); n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Prostrate); yield return Wait(1f); break;
                case "stacker_stack_more":
                    n.SetPose(ProceduralRig.Pose.Stack); yield return Wait(1.4f);
                    if (PropState.All.TryGetValue("field_pile", out var pile)) pile.transform.localScale *= 1.08f;
                    n.SetPose(keep); break;
                case "stacker_cower": n.SetPose(ProceduralRig.Pose.Cower); yield return Wait(1.2f); n.SetPose(keep); break;
                case "stacker_point_pile":
                    n.LookAt(At("z_field_pile")); n.SetPose(ProceduralRig.Pose.Point); Say(npcId, "s_take", 5f); yield return Wait(1f);
                    n.LookAt(Hero.position); yield return Wait(0.8f); n.LookAt(At("z_field_pile")); yield return Wait(0.6f); n.SetPose(keep); break;
                case "stacker_tilt": n.SetPose(ProceduralRig.Pose.Reach); yield return Wait(0.7f); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(1f); n.SetPose(keep); break;
                case "stacker_prostrate": case "villager_prostrate": n.SetPose(ProceduralRig.Pose.Prostrate); yield return Wait(0.8f); break;
                case "villager_lift_head": n.SetPose(ProceduralRig.Pose.HalfProstrate); n.LookAt(Hero.position); yield return Wait(1.3f); n.SetPose(ProceduralRig.Pose.Prostrate); break;
                case "silhouette_bow":
                    AudioHub.Play("crowd_bow", 0.5f);
                    foreach (var s in G.AllNpcs.Where(x => x.npcId.StartsWith("crowd") && Vector3.Distance(x.transform.position, n.transform.position) < 20f)) s.SetPose(ProceduralRig.Pose.Prostrate);
                    n.SetPose(ProceduralRig.Pose.Prostrate); yield return Wait(0.6f); break;
                case "glance":
                    n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(1f); n.SetPose(keep); break;
                default:
                    if (TryStoryReact(react, n, out var story)) { yield return story; break; }   // 이야기 반응 rx_*(DirectorScenes)
                    yield return Fallback(n, react, keep);
                    break;
            }
        }

        readonly HashSet<string> bowedOnce = new HashSet<string>();
        static bool BowLike(string r) => r == "villager_prostrate" || r == "silhouette_bow" || r == "stacker_prostrate" || r == "mother_bow" || r == "chief_bow";

        IEnumerator Fallback(NpcActor n, string react, ProceduralRig.Pose keep)
        {
            var r = react.ToLowerInvariant();
            var pose = r.Contains("kneel") ? ProceduralRig.Pose.Kneel : r.Contains("prostrate") || r.Contains("bow") ? ProceduralRig.Pose.Prostrate
                : r.Contains("tilt") ? ProceduralRig.Pose.Tilt : r.Contains("point") ? ProceduralRig.Pose.Point : r.Contains("cower") ? ProceduralRig.Pose.Cower : ProceduralRig.Pose.Nod;
            n.LookAt(Hero.position);
            n.SetPose(pose);
            yield return Wait(1.2f);
            if (pose == ProceduralRig.Pose.Nod || pose == ProceduralRig.Pose.Tilt || pose == ProceduralRig.Pose.Point) n.SetPose(keep);
        }

        IEnumerator KidStepIn(NpcActor n, string how)
        {
            n.StopFollow();
            switch (how)
            {
                case "stone": n.LookAt(At("z_pond_stone")); yield return Wait(1.2f); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.8f); break;
                case "grip": n.SetPose(ProceduralRig.Pose.Hug); yield return Wait(1f); break;
                case "up":
                    n.LookAt(lightShaft ? lightShaft.position : At("fall")); n.SetPose(ProceduralRig.Pose.PointUp); yield return Wait(1.3f);
                    if (n.Rig) n.Rig.FlickerNose(); yield return Wait(0.5f); break;
                default: n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Reach); yield return Wait(0.9f); break;
            }
            n.SetPose(ProceduralRig.Pose.Stand);
            var side = Hero.position + Hero.right * 0.9f;
            bool done = false; n.WalkTo(side, () => done = true);
            float t = 0; while (!done && t < 8f) { t += Time.deltaTime; yield return null; }
            n.LookAt(Hero.position);
        }

        IEnumerator ChiefProclaim(NpcActor n, bool tap)
        {
            if (tap) { n.SetPose(ProceduralRig.Pose.Kneel); yield return Wait(0.6f); AudioHub.Play("drop", 0.8f, 0.7f); n.SetPose(ProceduralRig.Pose.Stand); yield return Wait(0.4f); }
            n.LookAt(At("z_crowd_rows"));
            Say(n.npcId, "s_choose_out", 6f); AudioHub.Play("speak", 0.8f, 0.7f);
            yield return Wait(2.6f);
        }

        // ── 주인공 반응 ───────────────────────────────────
        public IEnumerator HeroAction(string op, string arg, List<object> raw)
        {
            switch (op)
            {
                case "react": yield return HeroReact(arg); break;
                case "pose": HeroPose(arg); break;
                case "moveTo": case "walk": yield return HeroWalk(raw.Count > 3 ? raw[3] : arg); break;
                case "warp": G.player.Warp(At(raw.Count > 3 ? raw[3] : arg)); break;
                default: yield return HeroReact(op); break;
            }
        }

        IEnumerator HeroReact(string react)
        {
            var rig = HeroRig;
            switch (react)
            {
                case "hero_stuck_gap":
                {
                    G.Busy = true;
                    var gap = At("z_fall_gap");
                    var from = Hero.position;
                    G.player.Stop();
                    float t = 0;
                    HeroFace("z_fall_gap");
                    while (t < 0.5f) { t += Time.deltaTime; Hero.position = Vector3.Lerp(from, Vector3.Lerp(from, gap, 0.6f), t / 0.5f); yield return null; }
                    if (rig) rig.SetPose(ProceduralRig.Pose.PushStuck);
                    AudioHub.Play("wrong", 0.4f, 1.2f);
                    yield return Wait(0.9f);
                    t = 0; var at = Hero.position;
                    while (t < 0.4f) { t += Time.deltaTime; Hero.position = Vector3.Lerp(at, from, t / 0.4f); yield return null; }
                    G.player.Warp(from);
                    if (rig) rig.SetPose(ProceduralRig.Pose.Tilt);
                    yield return Wait(0.8f);
                    if (rig) rig.SetPose(ProceduralRig.Pose.Stand);
                    G.ui.Toast(null, "몸이 커서 틈에 걸린다.", false);
                    G.Busy = false;
                    break;
                }
                case "hero_blocked":
                    if (rig) rig.SetPose(ProceduralRig.Pose.Push); yield return Wait(1.1f);
                    if (rig) rig.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(0.8f);
                    if (rig) rig.SetPose(ProceduralRig.Pose.Stand);
                    G.ui.Toast(null, "그려진 빗장이라 손이 미끄러진다. 옆 틈은 너무 좁다.", false);
                    break;
                case "hero_kneel_touch_pond":
                    if (rig) rig.SetPose(ProceduralRig.Pose.Kneel); yield return Wait(0.7f);
                    AudioHub.Play("piece", 0.7f, 0.75f); yield return Wait(0.4f); AudioHub.Play("piece", 0.7f, 0.75f);
                    yield return Wait(0.8f);
                    if (rig) rig.SetPose(ProceduralRig.Pose.Stand);
                    G.ui.Toast(null, "마른 먹처럼 단단하다. 물결도 없다.", false);
                    break;
                default:
                    if (TryStoryReact(react, null, out var heroStory)) { yield return heroStory; break; }
                    if (rig) rig.SetPose(ProceduralRig.Parse(react)); yield return Wait(1f); if (rig) rig.SetPose(ProceduralRig.Pose.Stand);
                    break;
            }
        }

        // ── 극 ──────────────────────────────────────────
        static readonly string[] Actors = { "actor_a", "actor_b", "actor_c" };

        public IEnumerator PlayLoop(PlayDef play)
        {
            while (true)
            {
                foreach (var line in play.Lines)
                {
                    yield return StagePose(J.Str(line.Raw, "pose"));
                    yield return Wait(line.Raw != null && line.Raw.TryGetValue("seconds", out var s) ? J.F(s) : 5f);
                }
            }
        }

        public IEnumerator PlayOnce(PlayDef play)
        {
            if (stageCenter) Shot(stageCenter.position, 22f, 13f, 10f, 30f, 1.6f);
            yield return Wait(1.2f);
            foreach (var line in play.Lines)
            {
                yield return StagePose(J.Str(line.Raw, "pose"));
                G.ui.ShowStageLine(line.Sentence, line.Stage);
                AudioHub.Play("page", 0.35f);
                yield return Wait(line.Raw != null && line.Raw.TryGetValue("seconds", out var s) ? J.F(s) : 6f);
            }
            G.ui.ShowStageLine(null, null);
            EndPlay();
            EndShot();
            yield return Wait(0.6f);
        }

        public void EndPlay()
        {
            foreach (var a in Actors) { var n = N(a); if (n) { n.SetPose(ProceduralRig.Pose.Stand); } }
            G.SetProp("lump_prop", "offstage");
        }

        IEnumerator StagePose(string pose)
        {
            var seat = At("z_doll_seat");
            switch (pose)
            {
                case "rehearse_1":
                    G.SetProp("lump_prop", "offstage");
                    for (int i = 0; i < Actors.Length; i++) { var n = N(Actors[i]); if (n) { n.WalkTo(seat + new Vector3(-2 + i * 2, 0, -1.8f)); } }
                    yield return Wait(1.6f);
                    foreach (var a in Actors) { var n = N(a); if (n) { n.LookAt(seat); n.SetPose(ProceduralRig.Pose.Prostrate); } }
                    break;
                case "rehearse_2":
                {
                    var a0 = N("actor_a");
                    foreach (var a in Actors) { var n = N(a); if (n) n.SetPose(a == "actor_a" ? ProceduralRig.Pose.Stand : ProceduralRig.Pose.HalfProstrate); }
                    if (a0) { a0.WalkTo(seat + new Vector3(0, 0, -0.9f)); }
                    break;
                }
                case "rehearse_3":
                {
                    var a0 = N("actor_a");
                    var fishProp = PropState.All.TryGetValue("fish_prop", out var fp) ? fp.transform.position : seat + new Vector3(4, 0, 0);
                    if (a0) a0.WalkTo(fishProp + new Vector3(0, 0, -0.6f));
                    break;
                }
                case "rehearse_4":
                {
                    G.SetProp("lump_prop", "onchair");
                    for (int i = 0; i < Actors.Length; i++) { var n = N(Actors[i]); if (n) { n.WalkTo(seat + new Vector3(-3 + i * 3, 0, -3.5f)); n.SetPose(ProceduralRig.Pose.Stand); } }
                    break;
                }
            }
            yield return null;
        }
    }
}
