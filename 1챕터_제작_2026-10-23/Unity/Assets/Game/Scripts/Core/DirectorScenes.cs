using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using OUAT.World;
using UnityEngine;

namespace OUAT.Core
{
    /// <summary>
    /// 1챕터 「내 자리 대신 가 줄래」(거짓말안 2026-10-23) 컷 장면과 이야기 반응.
    /// 장면 = sc_* (이름 = chapter1.json scenes[].id), 반응 = rx_*(NpcActor) / 주인공 반응 = rx_*() (이름 = react id).
    /// 깃발·물건 상태·크리처 자리는 대부분 사건(events)이 바꾸고, 여기서는 카메라·자세·클립·말·시간과 갈래에 따른 모습만 맡는다.
    /// 반응 rx_*는 Director.React / HeroReact의 기본 갈래에서 TryStoryReact로 부른다(메인 연결 — docs/메인요청.md).
    /// 이 파일에는 ShowThought를 쓰지 않는다(주인공 속말은 데이터에서 세고 8개 이하, 지금 7개).
    /// </summary>
    public partial class Director
    {
        // ═════════ 도구 ═════════
        bool Has(string flag) => G.State.Has(flag);
        IEnumerable<NpcActor> Grp(string id) => G.Group(id);
        IEnumerable<NpcActor> Crowds() => G.AllNpcs.Where(x => x && x.npcId.StartsWith("crowd") && x.gameObject.activeInHierarchy);
        static float Clip(NpcActor n, string clip) => n && n.Rig ? n.Rig.PlayClip(clip) : 0f;
        float HeroClip(string clip) { var r = HeroRig; return r ? r.PlayClip(clip) : 0f; }
        /// <summary>이름 붙은 클립을 틀고 그 길이만큼(없으면 fallback초) 기다림.</summary>
        IEnumerator ClipWait(NpcActor n, string clip, float fallback = 1f) { float len = Clip(n, clip); yield return Wait(len > 0f ? len : fallback); }
        IEnumerator HeroClipWait(string clip, float fallback = 1f) { float len = HeroClip(clip); yield return Wait(len > 0f ? len : fallback); }
        void Show(string id, bool on) { var n = N(id); if (n) n.gameObject.SetActive(on); }
        void Pulse(string id, float seconds) { foreach (var it in Interactable.All.Where(x => x.id == id)) it.Pulse(seconds); }
        void HeroVisible(bool on) { foreach (var r in Hero.GetComponentsInChildren<Renderer>()) r.enabled = on; }
        Vector3 HeroSide(float right, float forward = 0f) => Hero.position + Hero.right * right + Hero.forward * forward;
        /// <summary>키노피오가 동행 중이었다면(깃발 f_kid_follow) 반응 뒤 다시 따라오게.</summary>
        void Resume(NpcActor n) { if (n && n.npcId == "kinopio" && Has("f_kid_follow")) n.Follow(Hero); }

        // 키노피오 코: 주인공을 속일 때 한 마디씩 자람(갈면 줄어듦). ProceduralRig에 SetNoseGrow가 생기면 길이가 보임(메인요청) — 없으면 떨림만.
        float noseGrow;
        void Nose(NpcActor kid, float grow)
        {
            noseGrow = Mathf.Max(0f, grow);
            if (!kid || !kid.Rig) return;
            kid.Rig.SendMessage("SetNoseGrow", noseGrow, SendMessageOptions.DontRequireReceiver);
            kid.Rig.FlickerNose();
        }
        /// <summary>코가 한 마디 자라고 → 손등으로 가림(HideNose).</summary>
        IEnumerator NoseLie(NpcActor kid, float step = 2f)
        {
            if (!kid) yield break;
            Nose(kid, noseGrow + step);
            AudioHub.Play("quill", 0.25f, 1.4f);
            yield return ClipWait(kid, "HideNose", 0.6f);
        }
        /// <summary>남몰래 돌에 코를 갊(FileNose) — 갈고 나면 원래 길이.</summary>
        IEnumerator NoseFile(NpcActor kid, object where)
        {
            if (!kid) yield break;
            if (where != null) yield return Walk("kinopio", where, true, 6f);
            float len = Clip(kid, "FileNose");
            AudioHub.Play("file_nose", noseGrow > 2f ? 0.55f : 0.45f, 1.05f);
            yield return Wait(0.6f);
            if (noseGrow > 2f) AudioHub.Play("file_nose", 0.55f, 1.0f);
            yield return Wait(len > 0.6f ? len - 0.6f : 1.4f);
            Nose(kid, 0f);
        }
        /// <summary>광장 종(Bell). near = 광장 안에서 듣는 큰 종(bell_near), 아니면 먼 종(bell_far) — docs/오디오_적용.md 5-2.</summary>
        IEnumerator Ring(int times, float gap, float volume, bool near = false)
        {
            Prop("bell", "ring");
            for (int i = 0; i < times; i++) { AudioHub.Play(near ? "bell_near" : "bell_far", volume, 1f); yield return Wait(gap); }
            Prop("bell", "still");
        }
        static void Giggle(float volume = 0.6f, float pitch = 1.05f) => AudioHub.Play("kid_giggle", volume, pitch);
        static void Clack(int times = 1) { for (int i = 0; i < times; i++) AudioHub.PlayVariant("clack", 3, 0.35f); }

        /// <summary>
        /// 데이터 react가 Director.React 표에 없을 때 부르는 이야기 반응. n이 있으면 rx_name(NpcActor), 없으면(주인공) rx_name().
        /// 메인 연결: React 기본 갈래 `if (TryStoryReact(react, n, out var sr)) { yield return sr; break; }`, HeroReact 기본 갈래는 n = null.
        /// </summary>
        public bool TryStoryReact(string react, NpcActor n, out IEnumerator routine)
        {
            routine = null;
            if (string.IsNullOrEmpty(react)) return false;
            var m = typeof(Director).GetMethod("rx_" + react, BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public);
            if (m == null || m.ReturnType != typeof(IEnumerator)) return false;
            var ps = m.GetParameters();
            if (ps.Length == 1 && ps[0].ParameterType == typeof(NpcActor)) { if (!n) return false; routine = (IEnumerator)m.Invoke(this, new object[] { n }); return true; }
            if (ps.Length == 0 && !n) { routine = (IEnumerator)m.Invoke(this, null); return true; }
            return false;
        }

        // ═════════ 1막 구출과 첫 거짓말 ═════════

        // 1-1 떨어짐 — 빛구멍 아래로 사람 물건이 하나씩 떨어지고, 이어 주인공(사람 아이)이 굴러떨어져 쿵. 제목 → 일어나 두리번(속말 없음).
        static readonly string[] FallenItems = { "look_book", "look_umbrella", "look_clock" };

        IEnumerator sc_wake()
        {
            var rig = HeroRig;
            G.ui.FadeOut(0f);
            var hole = lightShaft ? lightShaft.position : At("fall");
            var land = At("z_hero_start");
            float yaw = G.followCamera.CurrentYaw;
            var items = FallenItems.Select(id => PropState.All.TryGetValue(id, out var ps) ? ps.transform : null).Where(x => x).ToList();
            var rest = items.Select(x => (x.position, x.rotation)).ToList();
            foreach (var x in items) x.position += Vector3.up * 30f;
            var agent = G.player.Agent;
            agent.enabled = false;
            Hero.position = land + Vector3.up * 30f;
            if (rig) rig.SetPose(ProceduralRig.Pose.Fall);

            Shot(new Vector3(hole.x, land.y + 7f, hole.z), 6f, 20f, yaw, 34f, 0f);
            G.followCamera.SnapFocus();
            AudioHub.Play("page", 0.5f, 0.6f);
            yield return G.ui.FadeIn(2.2f);
            yield return Wait(0.4f);
            for (int i = 0; i < items.Count; i++)
            {
                StartCoroutine(Drop(items[i], rest[i].position, rest[i].rotation, 1.0f, 0.55f + 0.1f * i));
                if (i == 0) Shot(new Vector3(hole.x, land.y + 3.5f, hole.z), 14f, 18f, yaw, 34f, 0f);
                yield return Wait(0.75f);
            }
            Shot(land, 24f, 13f, yaw, 34f, 0.6f);
            yield return Wait(1.0f);
            yield return Fall(Hero, land, 1.05f, rig != null && rig.HasClips);
            if (rig) rig.SetPose(ProceduralRig.Pose.LieDown);
            AudioHub.Play("drop", 0.9f, 0.55f);
            G.followCamera.Shake(0.35f);
            agent.enabled = true;
            G.player.Warp(land);
            yield return Wait(1.6f);
            G.ui.ShowChapterTitle("1장", G.Data.VillageName.Length > 0 ? G.Data.VillageName : "미완성 마을");
            yield return Wait(2.6f);
            Shot(land, 20f, 9f, yaw, 32f, 0.7f);
            if (rig && rig.HasClips) { rig.SetPose(ProceduralRig.Pose.GetUp); yield return Wait(2.1f); rig.SetPose(ProceduralRig.Pose.LookAround); yield return Wait(2.5f); rig.SetPose(ProceduralRig.Pose.Stand); }
            else { if (rig) rig.SetPose(ProceduralRig.Pose.Sit); yield return Wait(1.4f); if (rig) rig.SetPose(ProceduralRig.Pose.Stand); yield return Wait(0.7f); }
            // 넛지: 먼 가장자리에서 실루엣들이 자루를 끌고 지나감(물건 더미 쪽으로 눈이 가게)
            var edge = At("z_fall_edge");
            Shot(Vector3.Lerp(land, edge, 0.55f), 24f, 13f, yaw, 32f, 0.6f);
            foreach (var c in Grp("collectors")) { c.LookAt(At("fall_pile")); c.SetPose(ProceduralRig.Pose.Push); }
            AudioHub.Play("hook_scrape", 0.4f, 0.9f);
            yield return Wait(1.6f);
            foreach (var c in Grp("collectors")) c.SetPose(ProceduralRig.Pose.Stand);
            G.player.Face(At("look_book"));
            yield return Wait(0.6f);
        }

        IEnumerator Drop(Transform x, Vector3 to, Quaternion rot, float seconds, float pitch)
        {
            var from = to + Vector3.up * 16f;
            var spin = Random.rotationUniform;
            float t = 0;
            while (t < seconds)
            {
                t += Time.deltaTime; float k = Mathf.Clamp01(t / seconds);
                x.position = Vector3.Lerp(from, to, k * k);
                x.rotation = Quaternion.Slerp(spin, rot, k);
                yield return null;
            }
            AudioHub.Play("drop", 0.45f, 1.1f + pitch * 0.4f);
            t = 0;
            while (t < 0.3f) { t += Time.deltaTime; x.position = to + Vector3.up * Mathf.Sin(t / 0.3f * Mathf.PI) * 0.18f; yield return null; }
            x.position = to; x.rotation = rot;
        }

        IEnumerator Fall(Transform hero, Vector3 to, float seconds, bool clipTumble = false)
        {
            var from = to + Vector3.up * 16f;
            var face = hero.rotation;
            float t = 0;
            while (t < seconds)
            {
                t += Time.deltaTime; float k = Mathf.Clamp01(t / seconds);
                hero.position = Vector3.Lerp(from, to, k * k);
                if (!clipTumble) hero.rotation = face * Quaternion.Euler(k * 540f, 0, k * 200f);
                yield return null;
            }
            hero.position = to; hero.rotation = face;
        }

        // 1-2 자루 — 수거꾼이 물건을 쓸어 담고 주인공도 우산째 자루에 담김. 천 너머로 달려온 작은 목각 아이가 「귀한손님」을 두 번 외치자 모두 얼어붙고, 자루를 풀어 엎드림.
        IEnumerator sc_sack()
        {
            var boss = N("collector_boss"); var kid = N("kinopio");
            G.player.Stop();
            var land = Hero.position;
            var pile = At("fall_pile");
            var edge = At("z_fall_edge");
            int i = 0;
            foreach (var c in Grp("collectors")) { c.Warp(edge + new Vector3(-0.6f * i, 0, 0.8f * i)); i++; }
            if (boss) boss.Warp(edge + new Vector3(0.8f, 0, -1.0f));
            Shot(Vector3.Lerp(land, edge, 0.5f), 26f, 12f, null, 32f, 0.6f);
            AudioHub.Play("hook_scrape", 0.6f);
            i = 0;
            foreach (var c in Grp("collectors")) { c.WalkTo(pile + new Vector3(Mathf.Cos(i * 2.1f), 0, Mathf.Sin(i * 2.1f)) * 1.6f); i++; }
            if (boss) yield return Walk("collector_boss", "z_collector_fall", true, 6f);
            HeroFace("collector_boss");
            yield return Wait(0.6f);
            foreach (var c in Grp("collectors")) Clip(c, "Grab");
            AudioHub.Play("sack", 0.5f); 
            if (boss) { boss.LookAt(pile); Say("collector_boss", "s_we_take", 4.5f); yield return ClipWait(boss, "Grab", 1.4f); }
            AudioHub.Play("sack", 0.5f, 1.05f);
            // 주인공도 우산째 자루에
            if (boss) { boss.LookAt(Hero.position); yield return Walk("collector_boss", HeroSide(0f, 1.0f), true, 3f); }
            HeroClip("Startle");
            yield return Wait(0.5f);
            Prop("sack", "closed");
            HeroVisible(false);
            AudioHub.Play("sack", 0.9f, 0.85f);
            yield return G.ui.FadeOutRoutine(0.5f);
            // 어둠: 천 너머 달려오는 발소리
            AudioHub.Play("kid_run", 0.45f);
            yield return Wait(1.0f);
            if (kid)
            {
                kid.gameObject.SetActive(true);
                kid.Warp(land + (edge - land).normalized * 3.5f + Vector3.right * 0.6f);
                kid.LookAt(boss ? boss.transform.position : land);
            }
            yield return Wait(0.4f);
            Shot(Vector3.Lerp(land, kid ? kid.transform.position : land, 0.5f), 22f, 9f, null, 30f, 0.8f);
            yield return G.ui.FadeIn(0.8f);
            if (kid)
            {
                yield return Walk("kinopio", land + (kid.transform.position - land).normalized * 1.4f, true, 3f);
                kid.LookAt(boss ? boss.transform.position : land);
                Clip(kid, "ShoutWord"); Say("kinopio", "s_guest", 2.4f); AudioHub.Play("speak", 0.8f, 1.5f);
                yield return Wait(1.3f);
                kid.SetPose(ProceduralRig.Pose.Point);
                yield return Wait(0.6f);
                Clip(kid, "ShoutWord"); Say("kinopio", "s_guest", 2.4f); AudioHub.Play("speak", 0.8f, 1.6f);
                yield return Wait(1.3f);
            }
            // 얼어붙음 → 자루를 풀고 엎드림. 우두머리만 반쯤 엎드린 채 훑어봄
            foreach (var c in Grp("collectors")) c.SetPose(ProceduralRig.Pose.Still);
            if (boss) boss.SetPose(ProceduralRig.Pose.Still);
            yield return Wait(1.0f);
            Prop("sack", "open");
            HeroVisible(true);
            AudioHub.Play("sack", 0.7f, 1.1f);
            HeroPose("get_up");
            yield return Wait(1.2f);
            Clack(4);
            foreach (var c in Grp("collectors")) { c.LookAt(Hero.position); c.SetPose(ProceduralRig.Pose.Prostrate); }
            if (boss) { boss.LookAt(Hero.position); boss.SetPose(ProceduralRig.Pose.HalfProstrate); }
            HeroPose("stand");
            yield return Wait(1.4f);
        }

        // 1-3 첫 말 — 「나」「너」(거울처럼 뒤집힌 두 글자), 「너→이다→귀한손님」. 우두머리의 의심 「너→이다→물건」. 키노피오가 내 손을 내 가슴에 대 줌 → 판이 열림(사건 board).
        IEnumerator sc_first_words()
        {
            var kid = N("kinopio"); var boss = N("collector_boss");
            if (!kid) yield break;
            yield return Walk("kinopio", HeroSide(1.0f, 0.9f), true, 3f);
            kid.LookAt(Hero.position);
            Shot(Vector3.Lerp(Hero.position, kid.transform.position, 0.5f), 20f, 7.5f, null, 30f, 0.8f);
            G.ui.ShowNameplate(kid, "키노피오");
            yield return Wait(0.6f);
            Say("kinopio", "s_i", 3.2f); yield return ClipWait(kid, "PointSelf", 1.2f);
            yield return Wait(0.5f);
            Say("kinopio", "s_you", 3.2f); yield return ClipWait(kid, "PointOther", 1.2f);
            yield return Wait(0.5f);
            // 「너→이다→귀한손님」은 **주인공을 가리킨 채** 띄우고(너 = 주인공), 1.5초 뒤 엎드린 수거꾼 쪽으로 손을 폄(QA P1-8)
            kid.LookAt(Hero.position);
            Say("kinopio", "s_you_guest", 5.5f);
            yield return ClipWait(kid, "PointOther", 1.2f);
            yield return Wait(0.3f);
            if (boss) kid.LookAt(boss.transform.position);
            yield return ClipWait(kid, "Reach", 1.2f);   // 손을 폄
            kid.LookAt(Hero.position);
            kid.SetPose(ProceduralRig.Pose.Stand);
            if (boss)
            {
                Shot(Vector3.Lerp(Hero.position, boss.transform.position, 0.6f), 22f, 9f, null, 30f, 0.9f);
                boss.SetPose(ProceduralRig.Pose.Stand);
                boss.LookAt(At("sack")); yield return Wait(0.7f);
                boss.LookAt(Hero.position); boss.SetPose(ProceduralRig.Pose.Point);
                Say("collector_boss", "s_you_thing", 6f);
                yield return Wait(2.6f);
                boss.SetPose(ProceduralRig.Pose.Stand);
            }
            // 키노피오가 주인공 손을 잡아 주인공 자신의 가슴에 대 줌(화-09)
            Shot(Vector3.Lerp(Hero.position, kid.transform.position, 0.5f), 18f, 5.5f, null, 28f, 0.7f);
            kid.LookAt(Hero.position);
            yield return ClipWait(kid, "TugSleeve", 1.0f);
            HeroPose("hug");
            yield return Wait(1.2f);
            HeroPose("stand");
        }

        // 1-3 결과 — 우두머리가 가방을 두 손으로 받쳐 들고 「우리→가져가다→물건」, 언덕 가장자리로 떠남(가방이 첫 목표). 키노피오가 빛구멍 아래 「귀한손님→가다→위」 — 코가 한 마디(첫 거짓말).
        IEnumerator sc_d1_after()
        {
            var kid = N("kinopio"); var boss = N("collector_boss");
            if (boss)
            {
                Shot(Vector3.Lerp(Hero.position, boss.transform.position, 0.5f), 24f, 9f, null, 30f, 0.8f);
                if (Has("f_d1_doubt")) { boss.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(0.9f); }
                yield return Walk("collector_boss", HeroSide(0f, 0.9f), true, 3f);
                boss.LookAt(Hero.position);
                Shot(Vector3.Lerp(Hero.position, boss.transform.position, 0.5f), 18f, 4.5f, null, 28f, 0.7f);   // 가방이 넘어가는 것을 가까이(QA P1-9)
                yield return ClipWait(boss, "Grab", 1.2f);
                Prop("hero_bag", "taken"); Prop("boss_bag", "shown");
                AudioHub.Play("rope", 0.4f, 1.4f);
                yield return ClipWait(boss, "Offer", 1.2f);   // 두 손으로 받쳐 듦
                Shot(Vector3.Lerp(Hero.position, boss.transform.position, 0.5f), 24f, 9f, null, 30f, 0.8f);
                Say("collector_boss", "s_we_take", 5f);
                boss.SetPose(ProceduralRig.Pose.Stand);
                bool done = false;
                boss.WalkTo(At("z_fall_edge"), () => done = true);
                foreach (var c in Grp("collectors")) { c.SetPose(ProceduralRig.Pose.Stand); c.WalkTo(At("z_fall_edge")); }
                float t = 0; while (!done && t < 5f) { t += Time.deltaTime; yield return null; }
                boss.Warp(At("z_cart"));
                foreach (var c in Grp("collectors")) c.Warp(At("z_depot"));
            }
            if (!kid) yield break;
            // 소매를 끌어 빛구멍 아래로
            yield return Walk("kinopio", HeroSide(0.5f, 0.3f), true, 3f);
            yield return ClipWait(kid, "TugSleeve", 1.0f);
            yield return HeroWalk("z_light_spot", 6f);
            yield return Walk("kinopio", HeroSide(1.0f, 0.4f), true, 3f);
            var hole = lightShaft ? lightShaft.position : At("fall");
            Shot(Hero.position, 16f, 8f, null, 34f, 1.2f);
            kid.LookAt(hole); kid.SetPose(ProceduralRig.Pose.PointUp);
            Say("kinopio", "s_guest_up", 6f);
            yield return Wait(1.8f);
            HeroPose("lookup");
            // 코: 고정 카메라 그대로 — 눈치 빠른 사람만 봄
            yield return NoseLie(kid);
            kid.SetPose(ProceduralRig.Pose.Stand);
            kid.LookAt(At("z_ladder"));
            yield return Wait(1.4f);
            HeroPose("stand");
        }

        // 1-4 걸쇠 앞 — 키노피오가 걸쇠에 손을 뻗다 거둠(자격) → 주인공을 봄
        IEnumerator sc_kid_reach_latch()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            G.player.Stop();
            Shot(Vector3.Lerp(Hero.position, At("z_ladder"), 0.6f), 28f, 9f, null, 32f, 0.6f);
            kid.LookAt(At("z_ladder"));
            yield return ClipWait(kid, "Reach", 2.0f);
            kid.SetPose(ProceduralRig.Pose.HalfProstrate);
            yield return Wait(0.8f);
            kid.SetPose(ProceduralRig.Pose.Stand);
            kid.LookAt(Hero.position);
            yield return Wait(0.7f);
            kid.LookAt(At("z_ladder"));
            Pulse("pz_ladder", 2.5f);
            yield return Wait(0.6f);
            kid.LookAt(Hero.position);
        }

        // 1-4 사다리 — 펼쳐진 사다리를 코로 툭. 틈에 머리를 넣었다 빼며 「안」, 주인공과 틈을 번갈아 가리키며 킬킬 「너→가다→안」(놀림)
        IEnumerator sc_ladder_tease()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            Shot(Vector3.Lerp(At("z_ladder"), At("z_fall_gap"), 0.5f), 28f, 9f, null, 32f, 0.5f);
            yield return Walk("kinopio", At("z_ladder") + (At("z_fall_gap") - At("z_ladder")).normalized * 0.8f, true, 4f);
            kid.LookAt(At("z_ladder")); kid.SetPose(ProceduralRig.Pose.Nod);
            AudioHub.Play("latch", 0.35f, 1.6f);
            yield return Wait(0.8f);
            yield return Walk("kinopio", "z_gap_side", true, 4f);
            kid.LookAt(At("z_fall_gap")); kid.SetPose(ProceduralRig.Pose.Push);
            yield return Wait(0.7f);
            kid.SetPose(ProceduralRig.Pose.Stand); kid.LookAt(Hero.position);
            Say("kinopio", "s_in", 3f);
            yield return Wait(1.6f);
            Say("kinopio", "s_you_go_in", 6f);
            yield return ClipWait(kid, "PointOther", 1.2f);
            kid.LookAt(At("z_fall_gap")); yield return Wait(0.4f);
            kid.LookAt(Hero.position);
            Giggle(0.6f, 1.1f);
            yield return ClipWait(kid, "Grin", 1.4f);
        }

        // 대화2 결과 — 키노피오가 몸을 납작하게 틈으로 들어가 빗장을 어깨로 들어 올림(첫 협동)
        IEnumerator sc_kid_squeeze()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            Shot(Vector3.Lerp(At("z_fall_gap"), At("z_fall_bolt"), 0.4f), 30f, 12f, null, 32f, 0.4f);
            yield return Walk("kinopio", "z_fall_gap", true, 5f);
            AudioHub.Play("drop", 0.3f, 1.7f);
            kid.Warp(At("z_kid_wait_below"));
            Shot(At("z_fall_bolt"), 30f, 10f, null, 32f, 0.4f);
            kid.LookAt(At("z_fall_bolt"));
            yield return Wait(0.6f);
            kid.SetPose(ProceduralRig.Pose.Push);
            yield return Wait(0.8f);
            Prop("bolt_fall", "lifted");
            AudioHub.Play("drop", 0.6f, 0.8f);
            yield return Wait(1.0f);
            kid.SetPose(ProceduralRig.Pose.Stand);
            kid.LookAt(Hero.position);
            kid.SetPose(ProceduralRig.Pose.Beckon);
            yield return Wait(1.2f);
            kid.SetPose(ProceduralRig.Pose.Stand);
        }

        // 1-5 검문 — 뒤틀린 나무 촌장이 가지로 길을 막음. 앉은 주민들이 안쪽으로 절하며 「몸→절하다→안」. 촌장이 주인공을 보고 가지로 마을 안쪽을 가리키며 「귀한손님→가다→안」
        IEnumerator sc_gate_check()
        {
            G.player.Stop();
            var chief = N("chief");
            var inner = AreaSystem.I != null && AreaSystem.I.ExitToward(At("plaza")) is AreaExit ex ? Game.Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y)) : At("z_chief_gate");
            Shot(At("z_chief_gate"), 24f, 13f, null, 32f, 1.2f);
            if (chief) { chief.LookAt(inner); chief.SetPose(ProceduralRig.Pose.Still); }
            yield return Wait(1.0f);
            foreach (var id in new[] { "gate_a", "gate_b" }) { var n = N(id); if (n) { n.LookAt(inner); n.SetPose(ProceduralRig.Pose.Prostrate); } }
            foreach (var n in Grp("crowd_gate")) { n.LookAt(inner); n.SetPose(ProceduralRig.Pose.Prostrate); }
            Clack(5);
            Say("gate_a", "s_body_bow_in", 5f);
            yield return Wait(2.4f);
            if (chief)
            {
                chief.LookAt(Hero.position); chief.SetPose(ProceduralRig.Pose.Stand);
                yield return Wait(0.8f);
                chief.LookAt(inner); chief.SetPose(ProceduralRig.Pose.Point);
                Say("chief", "s_guest_in", 6f); AudioHub.Play("speak", 0.7f, 0.6f);
                yield return Wait(2.4f);
                chief.LookAt(Hero.position); chief.SetPose(ProceduralRig.Pose.Stand);
            }
            var kid = N("kinopio");
            if (kid) { yield return Walk("kinopio", HeroSide(-0.9f, -0.4f), true, 4f); kid.LookAt(At("chief")); }
            yield return Wait(0.6f);
        }

        // 대화3 결과 — 길이 열림. 키노피오가 붉은 끈을 가리킨 뒤 문 너머로 손을 휘저음("이걸로 지나간다" — 통행증이라는 거짓). 코 한 마디 → 문 기둥 돌에 갊. 주민들이 광장 쪽으로 비켜 서며 절함(넛지)
        IEnumerator sc_gate_pass()
        {
            var kid = N("kinopio"); var chief = N("chief");
            var inner = AreaSystem.I != null && AreaSystem.I.ExitToward(At("plaza")) is AreaExit ex ? Game.Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y)) : At("z_gate_post");
            if (chief) { yield return Walk("chief", chief.transform.position + Vector3.Cross(Vector3.up, (inner - chief.transform.position).normalized) * 2.2f, true, 4f); chief.LookAt(Hero.position); chief.SetPose(ProceduralRig.Pose.HalfProstrate); }
            if (kid)
            {
                Shot(Vector3.Lerp(Hero.position, kid.transform.position, 0.5f), 22f, 7f, null, 30f, 0.8f);
                kid.LookAt(Hero.position); kid.SetPose(ProceduralRig.Pose.Point);
                yield return Wait(1.0f);
                kid.LookAt(inner); kid.SetPose(ProceduralRig.Pose.Beckon);
                yield return Wait(1.2f);
                kid.SetPose(ProceduralRig.Pose.Stand);
                yield return NoseLie(kid);
                Shot(At("z_gate_post"), 26f, 10f, null, 32f, 0.6f);
                yield return NoseFile(kid, "z_gate_post");
                AudioHub.Play("piece", 0.3f, 1.8f);   // 나무 부스러기 한 줌
            }
            foreach (var id in new[] { "gate_a", "gate_b" }) { var n = N(id); if (n) { n.WalkTo(n.transform.position + (n.transform.position - inner).normalized * 1.2f, null); } }
            yield return Wait(0.8f);
            foreach (var id in new[] { "gate_a", "gate_b" }) { var n = N(id); if (n) { n.LookAt(inner); n.SetPose(ProceduralRig.Pose.Prostrate); } }
            Shot(inner, 28f, 14f, null, 34f, 0.5f);
            AudioHub.Play("crowd_bow", 0.4f);
            yield return Wait(1.6f);
        }

        // ═════════ 2막 대접과 신뢰 ═════════

        // 2-1 광장 — 그려진 주민이 엎드려 「우리→절하다→귀한손님」, 배 불룩한 죽 주는 이가 국자를 내밀며 「귀한손님→먹다」
        IEnumerator sc_plaza_welcome()
        {
            G.player.Stop();
            var a = N("plaza_a"); var p = N("porridge");
            Shot(Vector3.Lerp(Hero.position, At("z_crowd_offer"), 0.5f), 26f, 13f, null, 32f, 0.8f);
            if (a) { a.LookAt(Hero.position); a.SetPose(ProceduralRig.Pose.Prostrate); }
            foreach (var n in Grp("crowd_plaza")) { n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Prostrate); }
            AudioHub.Play("crowd_bow", 0.6f);
            Say("plaza_a", "s_we_bow_guest", 5f);
            yield return Wait(2.6f);
            if (p)
            {
                yield return Walk("porridge", HeroSide(0.4f, 1.5f), true, 8f);
                p.LookAt(Hero.position);
                Shot(Vector3.Lerp(Hero.position, p.transform.position, 0.5f), 22f, 7f, null, 30f, 0.9f);
                Clip(p, "Offer");
                Say("porridge", "s_guest_eat", 6f);
                yield return Wait(2.2f);
            }
            // 배경: 주민에게 둘러싸인 동안 죽 가게 뒤에서 키노피오가 숫돌에 코를 갊(다가가면 이미 멀쩡한 얼굴)
            var kid = N("kinopio");
            if (kid) { kid.StopFollow(); kid.Warp(At("z_porridge") + new Vector3(-1.4f, 0, -1.2f)); kid.LookAt(At("z_porridge")); Clip(kid, "FileNose"); AudioHub.Play("file_nose", 0.2f, 1.1f); Nose(kid, 0f); }
            yield return Wait(0.6f);
        }

        // 대화4 결과 — 가방을 멘 수거꾼이 광장 끝을 지나 수레 길로 꺾음(가방 끈이 흔들림). 키노피오가 가리키고 앞장섬
        IEnumerator sc_cart_passes()
        {
            var boss = N("collector_boss"); var kid = N("kinopio");
            var exit = AreaSystem.I != null && AreaSystem.I.ExitToward(At("z_cart")) is AreaExit ex ? Game.Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y)) : At("z_bell");
            if (boss)
            {
                boss.Warp(At("z_back_corner"));
                boss.SetPose(ProceduralRig.Pose.Stand);
                Shot(Vector3.Lerp(At("z_back_corner"), exit, 0.5f), 26f, 15f, null, 34f, 0.6f);
                AudioHub.Play("cart", 0.4f, 0.9f);
                Prop("boss_bag", "shown");
                bool done = false; boss.WalkTo(exit, () => done = true);
                yield return Wait(1.2f);
                Shot(boss.transform.position, 18f, 4f, null, 28f, 1.0f);   // 가방 끈이 흔들림(1초)
                yield return Wait(1.0f);
                Shot(Vector3.Lerp(At("z_back_corner"), exit, 0.5f), 26f, 15f, null, 34f, 0.6f);
                float t = 0; while (!done && t < 7f) { t += Time.deltaTime; yield return null; }
                boss.Warp(At("z_cart"));
            }
            if (kid) { kid.StopFollow(); kid.LookAt(exit); kid.SetPose(ProceduralRig.Pose.Point); yield return Wait(1.2f); kid.LookAt(Hero.position); kid.SetPose(ProceduralRig.Pose.Beckon); yield return Wait(1.0f); kid.SetPose(ProceduralRig.Pose.Stand); }
        }

        // 2-2 창고 — 문을 막은 실루엣 둘 → 키노피오가 통 위에서 엉덩이춤 + 숟가락 딱딱 → 실루엣들이 그쪽을 봄 → 주인공이 지나감(자동).
        // 수레 앞에 무릎 꿇은 우두머리 「우리→바치다→물건」. 그 사이 키노피오가 붉은 끈 바구니 뚜껑을 발로 닫음 → 코 한 마디 → 수레 바퀴에 갊
        IEnumerator sc_depot_arrive()
        {
            G.player.Stop();
            var kid = N("kinopio"); var boss = N("collector_boss");
            Prop("boss_bag", "hidden");   // 가방은 수레 꼭대기에(satchel on_cart)
            var cs = Grp("collectors").ToList();
            var teacher = Has("f_d4_teacher") ? N("porridge") : null;
            if (teacher) { teacher.LookAt(At("cart")); Say("porridge", "s_thing", 3f); }
            var gate = Vector3.Lerp(Hero.position, At("z_cart"), 0.45f);
            for (int i = 0; i < cs.Count && i < 2; i++) { cs[i].Warp(gate + new Vector3(0, 0, i == 0 ? -0.7f : 0.7f)); cs[i].LookAt(Hero.position); cs[i].SetPose(ProceduralRig.Pose.Stand); }
            Shot(gate, 26f, 10f, null, 32f, 0.7f);
            yield return Wait(1.0f);
            if (kid)
            {
                kid.StopLead();
                yield return Walk("kinopio", "z_depot_barrel", true, 5f);
                kid.LookAt(gate);
                for (int i = 0; i < 4; i++) { kid.SetPose(i % 2 == 0 ? ProceduralRig.Pose.Nod : ProceduralRig.Pose.Tilt); AudioHub.PlayVariant("clack", 3, 0.55f); yield return Wait(0.35f); }   // 나무 숟가락 두 개를 딱딱
                Clip(kid, "Grin"); Giggle();
                foreach (var c in cs) c.LookAt(kid.transform.position);
                yield return Wait(0.8f);
            }
            yield return HeroWalk(At("z_cart") + new Vector3(-1.6f, 0, -0.6f), 6f);
            if (teacher) { teacher.LookAt(At("z_cart") + Vector3.up * 2f); Say("porridge", "s_up", 3f); yield return Wait(1.6f); teacher.LookAt(At("z_depot")); Say("porridge", "s_in", 3f); yield return Wait(1.6f); }   // 물건마다 이름 한 글자(QA P2-11)
            Shot(At("z_cart"), 24f, 9f, null, 32f, 0.8f);
            if (boss)
            {
                boss.LookAt(At("z_cart"));
                boss.SetPose(Has("f_d1_doubt") ? ProceduralRig.Pose.HalfProstrate : ProceduralRig.Pose.Kneel);
                Say("collector_boss", "s_we_offer", 6f);
                if (Has("f_d1_doubt")) { yield return Wait(0.8f); boss.LookAt(Hero.position); }
                yield return Wait(2.2f);
            }
            // 붉은 끈 바구니 뚜껑
            if (kid)
            {
                yield return Walk("kinopio", "z_cord_basket", true, 5f);
                kid.LookAt(At("z_cord_basket")); kid.SetPose(ProceduralRig.Pose.Push);
                yield return Wait(0.4f);
                Prop("cord_basket", "closed");
                AudioHub.Play("drop", 0.25f, 1.5f);
                kid.SetPose(ProceduralRig.Pose.Stand);
                yield return NoseLie(kid);
                yield return NoseFile(kid, At("z_cart_lock") + new Vector3(0.9f, 0, 0.6f));
                kid.LookAt(Hero.position);
            }
            if (boss) boss.LookAt(Hero.position);
        }

        // 대화5 결과 — 가방 끈이 바퀴 쇠 고정쇠에 물려 있음(크리처는 자격 없음)
        IEnumerator sc_d5_after()
        {
            var boss = N("collector_boss");
            Shot(At("z_cart_lock"), 36f, 5.5f, null, 30f, 0.3f);
            Pulse("pz_cart", 3f);
            if (boss)
            {
                boss.LookAt(At("z_cart_lock"));
                yield return ClipWait(boss, "Reach", 1.2f);
                boss.SetPose(Has("f_d5_latch") ? ProceduralRig.Pose.Stand : ProceduralRig.Pose.HalfProstrate);
                if (Has("f_d5_latch")) { yield return Walk("collector_boss", boss.transform.position + (boss.transform.position - At("z_cart_lock")).normalized * 1.4f, true, 3f); boss.LookAt(Hero.position); }
            }
            yield return Wait(1.0f);
        }

        // 장치2 뒤 — 가방을 되찾음. 키노피오가 손가락을 입에 대고 골목 쪽으로 손짓, 발끝 걸음
        IEnumerator sc_bag_back()
        {
            var kid = N("kinopio");
            Shot(Hero.position, 22f, 7f, null, 30f, 0.8f);
            HeroPose("hug");
            AudioHub.Play("rope", 0.4f, 1.3f);
            yield return Wait(1.4f);
            HeroPose("stand");
            if (Has("f_d5_spoon")) Prop("hero_spoon", "shown");
            if (kid)
            {
                kid.LookAt(Hero.position);
                yield return ClipWait(kid, "HideNose", 0.6f);   // 손가락을 입에(가장 가까운 클립)
                kid.SetPose(ProceduralRig.Pose.Beckon);
                yield return Wait(1.2f);
                kid.SetPose(ProceduralRig.Pose.Stand);
            }
        }

        // 2-3 골목 — 집집 문 앞 의자에 천 덮은 덩어리, 주민이 천 위를 닦음. 키노피오가 자기 집 앞에서 걸음을 빨리하고 창문을 등으로 가린 채 씩 웃음 → 코 한 마디 → 문틀에 갊
        IEnumerator sc_alley_walk()
        {
            AudioHub.Music("music_village2");
            var kid = N("kinopio");
            Shot(At("z_lump"), 26f, 11f, null, 32f, 0.6f);
            Pose("mother", "wipe");
            foreach (var n in Grp("crowd_alley")) n.SetPose(ProceduralRig.Pose.Wipe);
            yield return Wait(2.0f);
            if (kid)
            {
                kid.StopLead();
                yield return Walk("kinopio", "z_kid_house", true, 8f);
                kid.LookAt(Hero.position);
                Shot(At("z_kid_house"), 24f, 9f, null, 32f, 0.6f);
                yield return ClipWait(kid, "Grin", 1.4f);
                yield return NoseLie(kid);
                yield return NoseFile(kid, At("z_kid_house") + new Vector3(0.8f, 0, 0.4f));
                kid.LookAt(Hero.position);
            }
        }

        // 2-3 고목 — 옹이를 세 번 두드리고 손가락을 입에 「나→숨기다→물건」. 껍질 문이 열림
        IEnumerator sc_knot_knock()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            Shot(At("z_bark_door"), 24f, 7f, null, 30f, 0.8f);
            kid.LookAt(At("bark_door"));
            for (int i = 0; i < 3; i++) { kid.SetPose(ProceduralRig.Pose.Push); AudioHub.Play("piece", 0.6f, 0.7f); yield return Wait(0.3f); kid.SetPose(ProceduralRig.Pose.Stand); yield return Wait(0.2f); }
            kid.LookAt(Hero.position);
            Clip(kid, "HideNose");
            Say("kinopio", "s_i_hide", 6f);
            yield return Wait(2.4f);
            Prop("bark_door", "open");
            AudioHub.Play("curtain", 0.5f, 0.7f);
            yield return Wait(1.0f);
        }

        // 2-3 굴 — 바치지 않고 숨겨 둔 사람 물건, 벽 숯 그림(빛구멍 아래 손잡은 두 아이), 구석 숫돌·부스러기(설명 없음).
        // 키노피오의 선물: 부스러기 한 조각을 돌로 깎아 손톱만 한 새를 만들어 줌(파랑새 색 옷을 가리키며) = 나무 새
        IEnumerator sc_hideout_show()
        {
            var kid = N("kinopio");
            G.player.Stop();
            Shot(At("z_hideout_stash"), 26f, 8f, null, 36f, 0.8f);
            if (kid) { kid.StopLead(); yield return Walk("kinopio", At("z_hideout_stash") + new Vector3(-0.9f, 0, -0.6f), true, 5f); kid.LookAt(At("z_hideout_stash")); kid.SetPose(ProceduralRig.Pose.Push); }
            AudioHub.Play("hook_scrape", 0.3f, 1.5f);   // 막대기로만 밀어 옮김
            yield return Wait(1.6f);
            Shot(At("z_hideout_drawing"), 22f, 7f, null, 36f, 0.9f);
            yield return Wait(1.8f);
            if (!kid) yield break;
            kid.SetPose(ProceduralRig.Pose.Stand);
            yield return Walk("kinopio", At("whetstone_hideout") + new Vector3(-0.6f, 0, 0.3f), true, 5f);
            kid.LookAt(At("whetstone_hideout")); kid.SetPose(ProceduralRig.Pose.Gather);
            for (int i = 0; i < 4; i++) { AudioHub.Play("quill", 0.35f, 1.2f); yield return Wait(0.35f); }
            kid.SetPose(ProceduralRig.Pose.Stand);
            yield return Walk("kinopio", HeroSide(0.3f, 0.8f), true, 5f);
            kid.LookAt(Hero.position);
            Shot(Vector3.Lerp(Hero.position, kid.transform.position, 0.5f), 18f, 5f, null, 30f, 0.7f);
            yield return ClipWait(kid, "Reach", 1.2f);
            kid.SetPose(ProceduralRig.Pose.Point);   // 파랑새 색 옷을 가리킴
            yield return Wait(1.0f);
            kid.SetPose(ProceduralRig.Pose.Stand);
            HeroPose("hug");
            yield return Wait(1.0f);
            HeroPose("stand");
        }

        // 놀이: 거울 조각 — 키노피오가 주인공 옆에 붙어 서서 거울 속 둘을 가리킴 「우리」. 거울 속 자기 코가 선뿐인 걸 보고 코를 쥐고 깔깔
        IEnumerator sc_play_mirror()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            yield return Walk("kinopio", HeroSide(0.7f, 0f), true, 4f);
            kid.LookAt(At("mirror_shard"));
            Shot(At("mirror_shard"), 22f, 5f, null, 30f, 0.6f);
            kid.SetPose(ProceduralRig.Pose.Point);
            Say("kinopio", "s_we", 4f);
            yield return Wait(1.8f);
            kid.SetPose(ProceduralRig.Pose.Tilt);
            yield return Wait(0.8f);
            yield return ClipWait(kid, "HideNose", 0.6f);
            Giggle(); yield return Wait(0.12f); Giggle(0.6f, 1.15f);
            yield return ClipWait(kid, "Grin", 1.4f);
        }

        // 놀이: 오르골 — 음악, 키노피오가 몸을 흔들다 벌렁 누움. 음악이 끝나면 천장 틈 빛을 보며 「우리→가다→위」(코 그대로 — 참말)
        IEnumerator sc_play_musicbox()
        {
            var kid = N("kinopio");
            Shot(At("music_box"), 22f, 6f, null, 32f, 0.6f);
            AudioHub.Music("");
            AudioHub.Loop("musicbox", "musicbox", 0.7f);   // 39초 곡 — 놀이가 끝나면 태엽 풀리듯 줄임
            for (int i = 0; i < 10; i++)
            {
                if (kid) kid.SetPose(i % 2 == 0 ? ProceduralRig.Pose.Nod : ProceduralRig.Pose.Tilt);
                yield return Wait(0.8f);
            }
            if (kid) { kid.SetPose(ProceduralRig.Pose.Sit); yield return Wait(2.0f); kid.SetPose(ProceduralRig.Pose.LookUp); }
            AudioHub.StopLoop("musicbox", 2.5f);
            yield return Wait(2.0f);
            Say("kinopio", "s_we_up", 5f);
            yield return Wait(2.6f);
            if (kid) kid.SetPose(ProceduralRig.Pose.Stand);
            AudioHub.Music("music_hideout");
        }

        // 놀이: 팽이 — 주인공이 돌리면 키노피오가 쫓다가 코로 팽이를 맞고 뒤로 넘어짐
        IEnumerator sc_play_top()
        {
            var kid = N("kinopio");
            Shot(At("spin_top"), 24f, 6f, null, 32f, 0.5f);
            HeroPose("reach");
            AudioHub.Play("top_spin", 0.6f);
            yield return Wait(0.6f);
            HeroPose("stand");
            if (!kid) yield break;
            var c = At("spin_top");
            for (int i = 0; i < 4; i++) { yield return Walk("kinopio", c + new Vector3(Mathf.Cos(i * 1.6f), 0, Mathf.Sin(i * 1.6f)) * 1.0f, true, 1.2f); }
            Clack(2);
            kid.SetPose(ProceduralRig.Pose.Sit);
            yield return Wait(1.2f);
            yield return ClipWait(kid, "Grin", 1.4f);
            kid.SetPose(ProceduralRig.Pose.Stand);
        }

        // 놀이: 숯 — 키노피오가 두 아이 옆에 파랑 망토 아이를 하나 더 그려 넣음 「나→그리다→너」
        IEnumerator sc_play_charcoal()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            yield return Walk("kinopio", At("z_hideout_drawing") + new Vector3(0.4f, 0, -0.6f), true, 4f);
            kid.LookAt(At("wall_drawing"));
            Shot(At("wall_drawing"), 18f, 5f, null, 30f, 0.8f);
            kid.SetPose(ProceduralRig.Pose.Gather);
            for (int i = 0; i < 4; i++) { AudioHub.Play("quill", 0.4f, 1.0f + i * 0.1f); yield return Wait(0.3f); }
            Prop("wall_hero", "shown");
            kid.SetPose(ProceduralRig.Pose.Stand);
            kid.LookAt(Hero.position);
            Say("kinopio", "s_draw_you", 5f);
            Giggle();
            yield return ClipWait(kid, "Grin", 1.4f);
        }

        // ── 둘째 굴 놀이: 숨기기(d_play_hide, 대-29) ──
        static readonly string[] HideSpots = { "stash", "whetstone_hideout", "hide_nest" };

        // 내가 숨긴 자리를 키노피오가 두 군데 헛짚고 찾음(깃발 f_hid_*가 내가 고른 자리)
        IEnumerator sc_kid_seeks()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            G.player.Stop();
            string mine = Has("f_hid_stash") ? "stash" : Has("f_hid_whet") ? "whetstone_hideout" : "hide_nest";
            HeroPose("crouch"); AudioHub.Play("sack", 0.3f, 1.4f);   // 나무 새를 그 자리에 밀어 넣음
            yield return Wait(0.8f);
            HeroPose("stand");
            yield return HeroWalk(At("z_hideout_talk"), 4f);
            HeroFace("kinopio");
            kid.SetPose(ProceduralRig.Pose.Stand);   // 눈을 뗌
            Giggle();
            foreach (var spot in HideSpots.Where(x => x != mine).Concat(new[] { mine }))
            {
                yield return Walk("kinopio", At(spot) + (At("z_hideout_talk") - At(spot)).normalized * 0.7f, true, 4f);
                kid.LookAt(At(spot)); kid.SetPose(ProceduralRig.Pose.Gather);
                AudioHub.PlayVariant("clack", 3, 0.35f);
                yield return Wait(1.0f);
                if (spot != mine) { kid.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(0.7f); }
            }
            kid.SetPose(ProceduralRig.Pose.PointUp);   // 찾았다!
            Giggle(0.7f, 1.15f);
            yield return Wait(0.8f);
            kid.LookAt(Hero.position);
            yield return ClipWait(kid, "Grin", 1.4f);
            kid.SetPose(ProceduralRig.Pose.Stand);
        }

        // 둥지 헝겊 밑에서 나무 새를 찾음 — 키노피오가 깔깔, 벽 그림 쪽을 봄
        IEnumerator sc_seek_found()
        {
            var kid = N("kinopio");
            G.player.Stop();
            HeroPose("reach"); AudioHub.Play("sack", 0.4f, 1.3f);
            yield return Wait(0.9f);
            HeroPose("hug");   // 나무 새를 쥠
            if (kid)
            {
                kid.gameObject.SetActive(true);
                yield return Walk("kinopio", HeroSide(0.7f, 0.6f), true, 4f);
                kid.LookAt(Hero.position);
                Giggle(); yield return Wait(0.12f); Giggle(0.6f, 1.15f);
                yield return ClipWait(kid, "Grin", 1.4f);
                kid.LookAt(At("wall_drawing")); yield return Wait(0.6f);
            }
            HeroPose("stand");
        }

        // 「우리→숨기다→물건」 — 둘이 함께 숨긴 물건을 둥지 헝겊 밑으로
        IEnumerator sc_hide_together()
        {
            var kid = N("kinopio");
            G.player.Stop();
            Shot(At("hide_nest"), 22f, 5.5f, null, 32f, 0.6f);
            if (kid) { yield return Walk("kinopio", At("hide_nest") + new Vector3(0.6f, 0, -0.6f), true, 4f); kid.LookAt(At("hide_nest")); kid.SetPose(ProceduralRig.Pose.Push); }
            yield return HeroWalk(At("hide_nest") + new Vector3(-0.7f, 0, -0.7f), 4f);
            HeroFace("hide_nest"); HeroPose("crouch");
            for (int i = 0; i < 3; i++) { AudioHub.Play("hook_scrape", 0.25f, 1.5f); AudioHub.Play("sack", 0.25f, 1.3f); yield return Wait(0.6f); }
            HeroPose("stand");
            if (kid) { kid.SetPose(ProceduralRig.Pose.Stand); kid.LookAt(Hero.position); Say("kinopio", "s_we", 3f); Giggle(); yield return ClipWait(kid, "Grin", 1.4f); }
        }

        // 2-3 「형」 — 그림 앞에서 큰 아이를 짚고 자기 머리 위로 손을 올려 키를 재 보임 「형」 → 눈은 바닥 「형→가다→안」(대화6 their)
        IEnumerator sc_kid_brother()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            G.player.Stop();
            yield return Walk("kinopio", At("z_hideout_drawing") + new Vector3(-0.5f, 0, -0.5f), true, 4f);
            Shot(At("wall_drawing"), 18f, 6f, null, 32f, 0.8f);
            kid.LookAt(At("wall_drawing")); kid.SetPose(ProceduralRig.Pose.Point);
            yield return Wait(1.0f);
            kid.LookAt(Hero.position); kid.SetPose(ProceduralRig.Pose.PointUp);   // 자기 머리 위로 키를 잼
            Say("kinopio", "s_bro", 4f);
            yield return Wait(2.0f);
            kid.SetPose(ProceduralRig.Pose.Stand);
            kid.LookAt(kid.transform.position + kid.transform.forward * 2f + Vector3.down);
            yield return Wait(0.6f);
            Say("kinopio", "s_bro_in", 6f);
            yield return Wait(2.0f);
        }

        // 대화6 결과 — 키노피오가 주인공 가방을 보고 가슴을 내밂(배지를 꽂아 줄 수 있다는 신호, 선택)
        IEnumerator sc_d6_after()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            Shot(Vector3.Lerp(Hero.position, kid.transform.position, 0.5f), 18f, 5.5f, null, 30f, 0.7f);
            kid.LookAt(Hero.position);
            yield return Wait(0.8f);
            kid.SetPose(ProceduralRig.Pose.Hug);   // 가슴을 내밂
            yield return Wait(1.4f);
            kid.SetPose(ProceduralRig.Pose.Stand);
            if (Has("f_d6_promise")) { kid.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.8f); kid.SetPose(ProceduralRig.Pose.Stand); }
        }

        // 선물: 파랑새 배지 — 사람 물건이라 손으로 못 받고 가슴을 내밂 → 꽂아 줌 → 파란 반짝임
        IEnumerator sc_badge_gift()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            G.player.Stop();
            HeroFace("kinopio");
            Shot(Vector3.Lerp(Hero.position, kid.transform.position, 0.5f), 16f, 4.5f, null, 28f, 0.6f);
            kid.LookAt(Hero.position);
            kid.SetPose(ProceduralRig.Pose.Hug);
            yield return Wait(0.6f);
            HeroPose("reach");
            yield return Wait(1.0f);
            Prop("kid_badge", "shown");
            AudioHub.Play("confirm", 0.35f, 1.4f);
            HeroPose("stand");
            yield return Wait(0.6f);
            kid.SetPose(ProceduralRig.Pose.Stand);
            Giggle();
            yield return ClipWait(kid, "Grin", 1.4f);
        }

        // 첫 종소리 — 키노피오가 벌떡 일어나 밭 쪽으로 손짓. 골목 주민 행렬이 한 방향으로 흐름
        IEnumerator sc_first_bell()
        {
            var kid = N("kinopio");
            G.player.Stop();
            yield return Ring(1, 1.4f, 0.8f);
            if (kid)
            {
                kid.StopLead();
                kid.SetPose(ProceduralRig.Pose.Stand);
                kid.LookAt(Hero.position);
                yield return Wait(0.5f);
                var exit = AreaSystem.I != null && AreaSystem.I.ExitToward(At("field")) is AreaExit ex ? Game.Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y)) : At("field");
                kid.LookAt(exit); kid.SetPose(ProceduralRig.Pose.Beckon);
                yield return Wait(1.2f);
                kid.SetPose(ProceduralRig.Pose.Stand);
            }
            foreach (var n in Grp("crowd_alley")) n.WalkTo(At("z_cart_procession") + new Vector3(Random.Range(-2f, 2f), 0, Random.Range(-1.5f, 1.5f)));
            var m = N("mother"); if (m) m.WalkTo(At("z_cart_procession") + new Vector3(2f, 0, 1f));
        }

        // ═════════ 3막 물고기와 배신 ═════════

        // 3-1 밭 — 수레 행렬, 주민 행렬(수레 자국을 따라감). 키노피오가 주인공 소매를 꽉 쥠
        IEnumerator sc_field_procession()
        {
            G.player.Stop();
            Shot(Vector3.Lerp(At("z_cart_procession"), At("z_pond_stop"), 0.5f), 28f, 16f, null, 34f, 0.6f);
            Prop("cart", "at_pond");
            Prop("tracks", "visible");
            foreach (var n in Grp("crowd_field").Concat(Grp("collectors"))) n.WalkTo(At("z_pond_stop") + new Vector3(Random.Range(-3f, 3f), 0, Random.Range(-2f, 2f)));
            var boss = N("collector_boss"); if (boss) boss.WalkTo(At("z_pond_edge") + new Vector3(-1.2f, 0, 1.0f));
            yield return Wait(2.6f);
            var kid = N("kinopio");
            if (kid) { yield return Walk("kinopio", HeroSide(0.5f, 0.3f), true, 4f); kid.LookAt(Hero.position); yield return ClipWait(kid, "TugSleeve", 1.0f); kid.Follow(Hero, 1.0f); }
        }

        // 3-1 물고기(핵심, 약 1분 30초) — 우두머리가 수레를 웅덩이로 기울임 「우리→바치다→물건」, 모두 엎드림. 먹물 선으로 그린 듯한 물고기가 솟아 물건을 통째로 삼키고
        // 붉은 끈을 맨 덩어리 하나와 둘둘 말린 띠 하나를 뱉고 가라앉음. 꼬마 「물고기→뱉다」, 어른이 입을 막고 「몸→남다」.
        // 키노피오가 서둘러 「귀한손님→가다→위」 — 코가 눈에 띄게 쭉, 눈이 마주침 → 밭둑 돌로 뛰어가 등을 돌리고 갊. 띠는 광장으로, 어미가 덩어리를 안고 무릎 꿇음
        IEnumerator sc_fish_rises()
        {
            G.player.Stop();
            var boss = N("collector_boss"); var kid = N("kinopio");
            var pond = At("pond");
            Shot(At("z_pond_edge"), 24f, 13f, null, 34f, 1.0f);
            if (boss) { yield return Walk("collector_boss", At("z_pond_edge") + new Vector3(-0.8f, 0, 0.6f), true, 5f); boss.LookAt(pond); boss.SetPose(ProceduralRig.Pose.Push); }
            Say("collector_boss", "s_we_offer", 5f);
            AudioHub.Play("hook_scrape", 0.6f);
            AudioHub.StopLoop("cart", 1.0f);
            yield return Wait(1.8f);
            foreach (var n in G.AllNpcs.Where(x => x && x.npcId != "kinopio" && x.npcId != "fish" && x.gameObject.activeInHierarchy && Vector3.Distance(x.transform.position, Hero.position) < 25f)) { n.LookAt(pond); n.SetPose(ProceduralRig.Pose.Prostrate); }
            Clack(6);
            AudioHub.Music("");
            Shot(pond, 22f, 20f, null, 34f, 1.4f);
            yield return Wait(3.0f);                         // 정적 — 모두 엎드린 채
            Prop("cart", "emptied"); AudioHub.Play("drop", 0.5f, 0.7f);   // 물건이 미끄러져 들어감
            yield return Wait(2.4f);
            var surf = PondSurf(); if (surf) surf.Bulge(0.5f);
            yield return Wait(2.0f);
            if (surf) surf.Bulge(0.9f);                      // 웅덩이가 부풀고
            Shot(pond, 14f, 24f, null, 36f, 2.4f);
            yield return Wait(2.2f);
            if (fish) yield return fish.Burst(true, () => { AudioHub.Play("fish_spit", 0.9f); Prop("lump_spat", "shown"); Prop("band_spat", "shown"); });
            else { Prop("lump_spat", "shown"); Prop("band_spat", "shown"); }
            yield return Wait(2.4f);                         // 가라앉은 뒤 고요
            Shot(At("z_lump_spat"), 16f, 6f, null, 30f, 0.6f);   // 뱉은 덩어리(붉은 끈)와 띠
            yield return Wait(2.6f);
            // 주민들 머리 위로 「물고기」
            Say("field_elder", "s_fish", 3f); Say("plaza_a", "s_fish", 3f); Say("field_kid", "s_fish", 3f);
            yield return Wait(1.6f);
            var fk = N("field_kid"); var fe = N("field_elder");
            Shot(At("z_lump_spat"), 22f, 9f, null, 30f, 0.6f);
            if (fk) { fk.SetPose(ProceduralRig.Pose.Stand); fk.LookAt(At("z_lump_spat")); fk.SetPose(ProceduralRig.Pose.Point); }
            Say("field_kid", "s_fish_spit_bare", 4f);
            yield return Wait(2.0f);
            if (fe) { fe.SetPose(ProceduralRig.Pose.Reach); fe.LookAt(fk ? fk.transform.position : pond); yield return Wait(0.6f); fe.LookAt(At("z_lump_spat")); fe.SetPose(ProceduralRig.Pose.Prostrate); }
            if (fk) fk.SetPose(ProceduralRig.Pose.Prostrate);
            Say("field_elder", "s_body_remain", 5f);
            yield return Wait(3.0f);
            // 키노피오의 두 번째 큰 거짓말
            if (kid)
            {
                kid.StopFollow();
                Shot(Vector3.Lerp(Hero.position, kid.transform.position, 0.5f), 18f, 5.5f, null, 30f, 0.8f);
                var hole = lightShaft ? lightShaft.position : At("fall");
                kid.LookAt(hole); kid.SetPose(ProceduralRig.Pose.PointUp);
                Say("kinopio", "s_guest_up", 4f);
                yield return Wait(1.0f);
                Shot(kid.transform.position + Vector3.up * 0.6f, 12f, 3.2f, null, 28f, 0.2f);   // 3m대 가까운 컷
                Nose(kid, 9f);   // 눈에 띄게 쭉(2.6배)
                AudioHub.Play("quill", 0.6f, 0.6f); AudioHub.Play("quill", 0.5f, 0.8f);
                kid.LookAt(Hero.position); kid.SetPose(ProceduralRig.Pose.Still);   // 가리기 전에 눈이 마주침
                yield return Wait(1.1f);
                Clip(kid, "HideNose");
                yield return Wait(0.4f);
                Clip(kid, "RunAway"); AudioHub.Play("kid_run", 0.45f);
                yield return Walk("kinopio", "z_field_stone", true, 6f);
                kid.LookAt(At("z_field_stone") + (At("z_field_stone") - Hero.position).normalized * 2f);
                yield return NoseFile(kid, null);
                Clip(kid, "Sulk");
            }
            // 주민 둘이 띠를 받들고 광장 쪽으로
            var bearers = Grp("crowd_field").Take(2).ToList();
            foreach (var b in bearers) { b.SetPose(ProceduralRig.Pose.Stand); b.WalkTo(At("z_lump_spat") + new Vector3(0.6f, 0, 0.6f)); }
            yield return Wait(1.2f);
            Prop("band_spat", "hidden");
            var ex2 = AreaSystem.I != null && AreaSystem.I.ExitToward(At("plaza")) is AreaExit ex ? Game.Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y)) : At("field");
            foreach (var b in bearers) b.WalkTo(ex2);
            // 어미가 덩어리를 안고 주인공 앞에 무릎 꿇음
            var m = N("mother");
            if (m)
            {
                m.SetPose(ProceduralRig.Pose.Stand);
                yield return Walk("mother", "z_pond_edge", true, 6f);
                m.LookAt(At("z_lump_spat")); m.SetPose(ProceduralRig.Pose.Gather);
                yield return Wait(0.8f);
                yield return HeroWalk(At("z_pond_edge") + (At("z_pond_stop") - At("z_pond_edge")).normalized * 1.6f, 5f);
                m.LookAt(Hero.position); m.SetPose(ProceduralRig.Pose.Kneel);
                Shot(Vector3.Lerp(Hero.position, m.transform.position, 0.5f), 20f, 6.5f, null, 30f, 0.8f);
                Say("mother", "s_body_remain", 6f);
                yield return Wait(2.0f);
            }
        }

        // 대화7 뒤 — 광장 종이 연달아. 띠를 든 주민과 행렬이 광장으로. 키노피오가 돌아와 앞장서지만 처음으로 뒤를 돌아보지 않음
        IEnumerator sc_bells_many()
        {
            G.player.Stop();
            yield return Ring(3, 1.6f, 0.8f);
            foreach (var n in G.AllNpcs.Where(x => x && (x.npcId.StartsWith("crowd") || x.npcId.StartsWith("field_")) && x.gameObject.activeInHierarchy)) n.SetPose(ProceduralRig.Pose.Stand);
            var ex2 = AreaSystem.I != null && AreaSystem.I.ExitToward(At("plaza")) is AreaExit ex ? Game.Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y)) : At("field");
            foreach (var n in Grp("crowd_field").Concat(Grp("crowd_plaza")).Concat(Grp("crowd_alley"))) n.WalkTo(ex2 + new Vector3(Random.Range(-1.5f, 1.5f), 0, Random.Range(-1.5f, 1.5f)));
            var kid = N("kinopio");
            if (kid) { kid.SetPose(ProceduralRig.Pose.Stand); yield return Walk("kinopio", HeroSide(1.4f, 2.0f), true, 6f); kid.LookAt(ex2); }
            Shot(Vector3.Lerp(Hero.position, ex2, 0.4f), 26f, 13f, null, 32f, 0.6f);
            yield return Wait(1.6f);
        }

        // 3-2 — 막이 다 열림, 주민들이 무대 앞에 앉음. 키노피오가 주인공 자리 옆에 앉아 기다림. 극 앞 그림판3(새김4)을 한 번 반짝임(어-18)
        IEnumerator sc_audience_sits()
        {
            G.player.Stop();
            Shot(At("z_stage"), 22f, 15f, null, 34f, 1.2f);
            foreach (var n in G.AllNpcs.Where(x => x && (x.npcId.StartsWith("crowd") || x.npcId.StartsWith("gate_") || x.npcId.StartsWith("field_") || x.npcId == "plaza_a" || x.npcId == "porridge") && x.gameObject.activeInHierarchy))
            { n.LookAt(At("z_stage")); n.SetPose(ProceduralRig.Pose.Sit); }
            var kid = N("kinopio");
            if (kid) { kid.StopLead(); yield return Walk("kinopio", At("z_audience_seat") + new Vector3(1.0f, 0, 0.3f), true, 8f); kid.LookAt(At("z_stage")); kid.SetPose(ProceduralRig.Pose.Sit); }
            yield return Wait(1.0f);
            Shot(At("z_board_chair"), 22f, 7f, null, 32f, 0.8f);
            Pulse("ins_board_chair", 3f);
            yield return Wait(1.6f);
            Shot(At("audience_seat"), 24f, 9f, null, 32f, 0.6f);
            Pulse("audience_seat", 3f);
            if (kid) { kid.LookAt(At("audience_seat")); kid.SetPose(ProceduralRig.Pose.Reach); for (int i = 0; i < 2; i++) { AudioHub.PlayVariant("clack", 3, 0.4f); yield return Wait(0.35f); } kid.SetPose(ProceduralRig.Pose.Sit); kid.LookAt(Hero.position); }   // 옆자리를 손바닥으로 두드림
            yield return Wait(0.8f);
        }

        // 3-2 — 주인공이 자리에 앉음 → 극(사건 play_day)
        IEnumerator sc_take_seat()
        {
            G.player.Stop();
            HeroFace("z_stage");
            HeroPose("seated");
            var kid = N("kinopio"); if (kid) { kid.LookAt(Hero.position); yield return Wait(0.4f); kid.LookAt(At("z_stage")); }
            AudioHub.Play("curtain", 0.6f);
            yield return Wait(1.0f);
        }

        // 3-2 극 뒤 — 막이 닫힘. 관객 전부가 천천히 고개를 돌려 주인공 망토의 붉은 끈을 보고 — 절함. 키노피오 자리가 비어 있음(2번 줄 때 빠져나감).
        // 키노피오 자리에서 골목 쪽으로 나무 부스러기가 띄엄띄엄(넛지). 배지를 달아 줬으면 골목 입구에서 파란 반짝임
        IEnumerator sc_after_play()
        {
            AudioHub.Play("curtain", 0.6f, 0.8f);
            AudioHub.StopLoop("crowd", 1.5f);
            Prop("stage", "idle");
            Shot(At("z_crowd_rows"), 22f, 13f, null, 34f, 1.0f);
            yield return Wait(1.0f);
            var watchers = G.AllNpcs.Where(x => x && x.npcId != "kinopio" && x.npcId != "fish" && x.gameObject.activeInHierarchy && Vector3.Distance(x.transform.position, Hero.position) < 16f).ToList();
            AudioHub.Music("music_truth", 0.34f);
            foreach (var n in watchers) { n.LookAt(Hero.position); AudioHub.PlayVariant("clack", 3, 0.3f); yield return Wait(0.08f); }
            yield return Wait(1.4f);
            Shot(Hero.position, 14f, 4.5f, null, 30f, 0.8f);   // 망토의 붉은 끈
            yield return Wait(1.6f);
            AudioHub.Play("crowd_bow", 0.7f); Clack(5);
            foreach (var n in watchers) n.SetPose(ProceduralRig.Pose.Prostrate);
            yield return Wait(1.6f);
            var kid = N("kinopio");
            if (kid && kid.gameObject.activeInHierarchy)
            {
                // 골목 쪽으로 뛰어나가는 뒷모습 1초(QA P1-3)
                var ex = AreaSystem.I != null ? AreaSystem.I.ExitToward(At("alley")) : null;
                var alleyExit = ex != null ? Game.Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y)) : At("z_back_corner");
                kid.SetPose(ProceduralRig.Pose.Stand); Clip(kid, "RunAway"); AudioHub.Play("kid_run", 0.35f);
                kid.WalkTo(alleyExit);
                Shot(Vector3.Lerp(kid.transform.position, alleyExit, 0.4f), 22f, 11f, null, 32f, 0.5f);
                yield return Wait(1.2f);
            }
            Shot(At("audience_seat") + new Vector3(1.0f, 0, 0.3f), 22f, 6f, null, 30f, 0.4f);   // 빈자리
            if (kid) kid.gameObject.SetActive(false);
            Prop("sawdust_trail", "shown");
            yield return Wait(2.0f);
            HeroPose("stand");
            if (Has("f_badge")) { AudioHub.Play("confirm", 0.25f, 1.6f); }
        }

        // 3-3 키노피오 집 — 천을 걷음: 덩어리 목께에 붉은 끈, 매듭이 주인공 망토 매듭과 똑같음(한 번 묶기/두 번 감기도). 그 순간 문간에 그림자 — 키노피오, 갈지 못한 긴 코, 손에 깎다 만 나무 새.
        // 2초 마주 봄 → 새를 떨어뜨리고 달아남. 창밖 이웃이 다정하게 「너→이다→귀한손님」, 빈 고리를 손으로 쓸어 보임
        IEnumerator sc_cloth_lifted()
        {
            G.player.Stop();
            HeroFace("brother_lump");
            HeroPose("reach");
            AudioHub.Play("rope", 0.5f, 0.7f);
            yield return Wait(0.8f);
            HeroPose("stand");
            Shot(At("brother_lump"), 16f, 3.2f, null, 28f, 0.7f);   // 덩어리 목의 매듭
            yield return Wait(2.0f);
            Shot(Hero.position, 16f, 3.2f, null, 28f, 0.7f);         // 내 망토 매듭
            yield return Wait(1.8f);
            var kid = N("kinopio");
            if (kid)
            {
                kid.gameObject.SetActive(true);
                kid.Warp(At("z_kid_house"));
                kid.LookAt(Hero.position); kid.SetPose(ProceduralRig.Pose.Still);
                Nose(kid, 9f);   // 갈지 못한 채 길게 뻗은 코(2.6배)
                AudioHub.Play("quill", 0.5f, 0.6f);
                Shot(kid.transform.position + Vector3.up * 0.6f, 12f, 3.4f, null, 28f, 0.2f);
                yield return Wait(1.0f);
                HeroFace("kinopio");
                Shot(Vector3.Lerp(Hero.position, kid.transform.position, 0.5f), 18f, 6f, null, 30f, 0.7f);
                yield return Wait(2.0f);
                AudioHub.Play("drop", 0.3f, 1.6f);   // 깎다 만 나무 새가 떨어짐
                yield return Wait(0.3f);
                Clip(kid, "RunAway"); AudioHub.Play("kid_run", 0.45f);
                var door = At("z_bark_door");
                bool done = false; kid.WalkTo(door, () => done = true);
                float t = 0; while (!done && t < 5f) { t += Time.deltaTime; yield return null; }
                AudioHub.Play("curtain", 0.5f, 0.6f);   // 껍질 문이 닫힘
                kid.Warp(At("z_hideout_door_in"));
            }
            var nb = N("neighbor");
            if (nb)
            {
                Shot(Vector3.Lerp(Hero.position, nb.transform.position, 0.5f), 20f, 7f, null, 30f, 0.8f);
                nb.LookAt(Hero.position); nb.SetPose(ProceduralRig.Pose.Nod);
                Say("neighbor", "s_you_guest", 6f);
                yield return Wait(1.8f);
                nb.LookAt(At("cord_hook")); nb.SetPose(ProceduralRig.Pose.Reach);   // 빈 고리를 쓸어 보임
                yield return Wait(1.4f);
                nb.SetPose(ProceduralRig.Pose.Stand); nb.LookAt(Hero.position);
            }
            foreach (var n in Grp("crowd_alley")) n.LookAt(At("z_bark_door"));   // 넛지: 골목 주민들이 고목 쪽으로 고개를 돌림
            if (Has("f_badge")) AudioHub.Play("confirm", 0.25f, 1.6f);
            yield return Wait(0.6f);
        }

        // 4-1 닫힌 굴 — 옹이 구멍으로 긴 코끝이 삐죽. 키노피오가 처음으로 자기를 두고 「나→이다→귀한손님」. 그 말을 하는 동안 코끝에서 긴 조각이 저절로 떨어짐(참말)
        IEnumerator sc_trunk_voice()
        {
            G.player.Stop();
            HeroFace("bark_door");
            Shot(At("bark_door"), 16f, 3.6f, null, 28f, 1.0f);   // 옹이로 삐죽 나온 긴 코끝
            Prop("door_nose", "long");
            yield return Wait(1.4f);
            G.ui.ShowStageLine("s_i_guest", "문 너머");          // 문 너머 목소리(키노피오는 굴 안 — 머리 위 말 대신 띠 한 줄)
            AudioHub.Play("speak", 0.5f, 1.2f);
            yield return Wait(2.2f);
            Prop("door_nose", "short");
            Nose(N("kinopio"), 0f);
            AudioHub.Play("piece", 0.7f, 0.9f);                  // 코 조각이 저절로 떨어짐(참말)
            Shot(At("bark_door") + Vector3.down * 0.6f, 10f, 2.6f, null, 28f, 0.2f);
            yield return Wait(2.2f);
            G.ui.ShowStageLine(null, null);
        }

        // 4-1 대화8 결과 — 갈래대로 문이 열림(따짐: 한참 조용하다 / 떠안음: 벌컥, 매듭을 쥐고 풀려다 주저앉음 / 함께: 천천히, 오르골을 밀어 줌).
        // 이어 키노피오가 굴 안 벽 그림 앞으로 앞장(사건 lead) — 고백은 그림 앞(sc_confession, QA P1-5)
        IEnumerator sc_door_opens()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            G.player.Stop();
            Shot(At("z_bark_door"), 20f, 6f, null, 30f, 0.8f);
            Prop("door_nose", "hidden");
            Prop("bark_door", "open");
            AudioHub.Play("curtain", 0.5f, Has("f_d8_take") ? 1.2f : 0.6f);
            kid.Warp(At("z_bark_door") + (At("z_hideout_door_in") - At("z_bark_door")).normalized * 0.9f);
            kid.LookAt(Hero.position);
            if (Has("f_d8_take"))
            {
                yield return Walk("kinopio", HeroSide(0f, 0.6f), true, 3f);
                yield return ClipWait(kid, "TugSleeve", 1.0f);   // 망토 매듭을 쥐고 풀려고 애씀 — 촌장 매듭이라 안 풀림
                yield return ClipWait(kid, "TugSleeve", 1.0f);
                kid.SetPose(ProceduralRig.Pose.Sit);
                yield return Wait(1.4f);
                kid.SetPose(ProceduralRig.Pose.Stand);
            }
            else if (Has("f_d8_together"))
            {
                kid.SetPose(ProceduralRig.Pose.Push);
                AudioHub.Play("hook_scrape", 0.3f, 1.5f);   // 오르골을 막대기로 밀어 줌
                yield return Wait(1.0f);
                kid.SetPose(ProceduralRig.Pose.Stand);
                HeroPose("reach");
                AudioHub.Music("");
                AudioHub.Play("musicbox_short", 0.7f);
                yield return Wait(3.0f);
                HeroPose("stand");
            }
            else
            {
                yield return Wait(1.8f);   // 따짐: 한참 조용하다 문이 열림, 고개를 숙인 채 주인공 옆을 지나 굴 안으로
                kid.SetPose(ProceduralRig.Pose.HalfProstrate);
                yield return Wait(1.0f);
                kid.SetPose(ProceduralRig.Pose.Stand);
            }
            kid.LookAt(At("z_hideout_drawing"));
            kid.SetPose(ProceduralRig.Pose.Beckon);
            yield return Wait(1.0f);
            kid.SetPose(ProceduralRig.Pose.Stand);
        }

        // 4-1 고백(셋 다 — 글자 없음) — 굴 안 벽 그림 앞. 먼저 그림을 크게: 대화6 결과(빛구멍까지 선 / 번진 얼굴 / 그대로)와 파랑 망토 아이.
        // 큰 아이에 손바닥 → 자기 가슴 → 주인공 망토의 끈 → 자기 빈 목 → 두 팔로 물고기 입이 닫히는 시늉 → 떪. 약속 갈래면 내내 눈은 바닥. 이어 둘째 종(길게)
        IEnumerator sc_confession()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            G.player.Stop();
            kid.StopLead();
            Shot(At("wall_drawing"), 16f, 4.2f, null, 30f, 0.9f);   // 벽 그림(대화6 결과가 그대로)
            yield return Wait(2.6f);
            yield return Walk("kinopio", At("z_hideout_drawing") + new Vector3(-0.4f, 0, -0.5f), true, 4f);
            bool down = Has("f_d6_promise");
            var floor = kid.transform.position + kid.transform.forward * 1.5f + Vector3.down * 1f;
            Shot(Vector3.Lerp(Hero.position, kid.transform.position, 0.6f), 16f, 4.8f, null, 28f, 0.6f);
            kid.LookAt(At("wall_drawing")); kid.SetPose(ProceduralRig.Pose.Reach);   // 큰 아이에 손바닥
            yield return Wait(1.6f);
            kid.LookAt(down ? floor : Hero.position);
            yield return ClipWait(kid, "PointSelf", 1.2f);
            kid.LookAt(Hero.position); kid.SetPose(ProceduralRig.Pose.Point);   // 주인공 망토의 끈
            yield return Wait(1.1f);
            if (down) kid.LookAt(floor);
            kid.SetPose(ProceduralRig.Pose.Hug);     // 자기 빈 목
            yield return Wait(1.2f);
            kid.SetPose(ProceduralRig.Pose.PointUp); // 두 팔로 물고기 입이 닫히는 시늉
            yield return Wait(0.7f);
            kid.SetPose(ProceduralRig.Pose.Cower);
            AudioHub.Play("drop", 0.3f, 0.6f);
            yield return Wait(1.6f);
            Shot(At("wall_drawing"), 18f, 4.6f, null, 30f, 0.9f);   // 숯 그림 속 파랑 망토 아이는 그대로
            yield return Wait(1.4f);
            if (Has("f_d8_accuse") && Has("f_badge")) { kid.SetPose(ProceduralRig.Pose.Reach); yield return Wait(0.8f); }   // 배지를 떼려다 손을 못 댐
            kid.SetPose(ProceduralRig.Pose.Stand);
            yield return Ring(2, 2.5f, 0.8f);   // 둘째 종, 길게
            AudioHub.Music(Has("f_d8_accuse") ? "music_truth" : "music_hideout");
            foreach (var n in Grp("crowd_alley")) n.WalkTo(At("plaza"));
            if (Has("f_d8_accuse")) { kid.SetPose(ProceduralRig.Pose.HalfProstrate); yield return Wait(0.6f); kid.SetPose(ProceduralRig.Pose.Stand); }
        }

        // 4-2 띠 — 그림판3 위에 3-1에서 뱉어진 띠가 새로 붙어 있음 「우리→바치다→귀한손님」. 모서리가 들떠 있고 그 종이만 누렇고 색이 있음(사람 종이)
        IEnumerator sc_band_glint()
        {
            G.player.Stop();
            Prop("band_new", "posted");
            Shot(At("z_board_chair"), 20f, 6.5f, null, 30f, 1.0f);
            yield return Wait(1.0f);
            Pulse("band_new", 3f);
            AudioHub.Play("page", 0.4f, 0.8f);
            yield return Wait(2.0f);
        }

        // 4-2 뒤 — 촌장 지팡이 소리, 주민 행렬이 웅덩이까지. 덜 그려진 횃불이 길을 따라 놓임
        IEnumerator sc_final_call()
        {
            G.player.Stop();
            for (int i = 0; i < 3; i++) { AudioHub.Play("drop", 0.6f, 0.45f); yield return Wait(0.7f); }   // 지팡이
            AudioHub.Music("music_procession", 0.34f);
            Prop("torches", "shown");
            var exit = AreaSystem.I != null && AreaSystem.I.ExitToward(At("field")) is AreaExit ex ? Game.Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y)) : At("z_bell");
            foreach (var n in G.AllNpcs.Where(x => x && x.npcId != "kinopio" && x.npcId != "fish" && x.npcId != "chief" && x.gameObject.activeInHierarchy && Vector3.Distance(x.transform.position, Hero.position) < 20f))
            { n.SetPose(ProceduralRig.Pose.Stand); n.WalkTo(exit + new Vector3(Random.Range(-1.2f, 1.2f), 0, Random.Range(-1.2f, 1.2f))); }
            Shot(Vector3.Lerp(Hero.position, exit, 0.5f), 26f, 14f, null, 34f, 0.6f);
            yield return Wait(2.4f);
        }

        // 4-3 줄 자리(slice3 pond_lineup3): 앞줄 0~7 · 뒷줄 8~15. 이름 있는 주민만 — 실루엣 무리는 단계(P8)가 밭 길에 둠.
        static readonly Vector3[] LineSpots =
        {
            new Vector3(54.85f, 0, -10.21f), new Vector3(53.91f, 0, -10.66f), new Vector3(53.04f, 0, -11.22f), new Vector3(52.24f, 0, -11.89f),
            new Vector3(51.53f, 0, -12.65f), new Vector3(50.92f, 0, -13.49f), new Vector3(50.41f, 0, -14.4f), new Vector3(50.02f, 0, -15.36f),
            new Vector3(54.67f, 0, -8.84f), new Vector3(53.48f, 0, -9.36f), new Vector3(52.38f, 0, -10.03f), new Vector3(51.38f, 0, -10.85f),
            new Vector3(50.49f, 0, -11.79f), new Vector3(49.73f, 0, -12.83f), new Vector3(49.12f, 0, -13.97f), new Vector3(48.67f, 0, -15.18f),
        };
        static readonly string[] LineWho = { "watcher", "plaza_a", "gate_a", "collector_boss", "mother", "porridge", "field_elder", "field_kid", "gate_b", "actor_a", "actor_b", "kinopio", null, "actor_c", null, null };

        void LineupPlace()
        {
            var pond = At("pond");
            for (int i = 0; i < LineSpots.Length; i++)
            {
                var id = LineWho[i]; if (id == null) continue;
                if (id == "watcher" && !Has("f_d3_watch")) continue;
                if (id == "mother" && Has("f_d7_truth")) continue;   // 어미 자리가 빔
                if (id == "kinopio" && !Has("f_d8_accuse")) continue;
                var n = N(id); if (!n) continue;
                n.gameObject.SetActive(true); n.StopFollow(); n.StopLead();
                n.Warp(At(LineSpots[i]));
                n.LookAt(pond);
                n.SetPose(id == "kinopio" ? ProceduralRig.Pose.Cower : ProceduralRig.Pose.Stand);
            }
            var chief = N("chief");
            if (chief) { chief.Warp(At("z_chief_pond")); chief.LookAt(Hero.position); chief.SetPose(ProceduralRig.Pose.Stand); }
            if (Has("f_d7_truth")) { var m = N("mother"); if (m) m.Warp(At("z_lump")); }
        }

        // 이어하기: 줄 자리만 다시
        IEnumerator sc_lineup_place() { LineupPlace(); yield return null; }

        // 4-3 막오름 — 웅덩이까지 늘어선 줄. 앞의 지킴이(대화3), 줄 틈을 여는 우두머리(대화5), 빈 자리(대화7). 웅덩이 앞 촌장. 키노피오 자리는 대화8 결과
        IEnumerator sc_pond_lineup()
        {
            G.player.Stop();
            LineupPlace();
            Shot(Vector3.Lerp(At("z_pond_stop"), At("pond"), 0.45f), 26f, 20f, null, 36f, 0.8f);
            yield return Wait(2.4f);
            if (Has("f_d3_watch")) { Shot(At(LineSpots[0]), 20f, 6f, null, 30f, 0.8f); yield return Wait(1.6f); }   // 끈 끝을 쥔 지킴이
            var boss = N("collector_boss");
            if (boss && Has("f_d5_latch"))
            {
                Shot(boss.transform.position, 22f, 8f, null, 30f, 0.8f);
                yield return Walk("collector_boss", boss.transform.position + (boss.transform.position - At("pond")).normalized * 1.2f, true, 3f);
                boss.LookAt(Hero.position); boss.SetPose(ProceduralRig.Pose.HalfProstrate);   // 줄 틈을 열어 줌
                yield return Wait(1.2f);
            }
            if (Has("f_d7_truth")) { Shot(At(LineSpots[4]), 22f, 7f, null, 30f, 0.6f); yield return Wait(1.6f); }   // 어미 자리가 빔
            var chief = N("chief");
            if (chief)
            {
                Shot(Vector3.Lerp(Hero.position, chief.transform.position, 0.5f), 22f, 9f, null, 32f, 1.2f);
                chief.SetPose(ProceduralRig.Pose.Point);
                AudioHub.Play("drum_stage", 0.8f);
                Say("chief", "s_guest_in", 6f);
                yield return Wait(2.4f);
                chief.SetPose(ProceduralRig.Pose.Stand);
            }
        }

        // 대화9 뒤 — 촌장이 비켜 서며 웅덩이 끝을 보임
        IEnumerator sc_d9_after()
        {
            var chief = N("chief");
            if (chief && !Has("f_d9_two")) { yield return Walk("chief", At("z_chief_pond") + (At("z_chief_pond") - At("pond")).normalized * 1.4f + Vector3.Cross(Vector3.up, (At("pond") - At("z_chief_pond")).normalized) * 1.6f, true, 4f); chief.LookAt(At("z_pond_bank")); chief.SetPose(ProceduralRig.Pose.HalfProstrate); }
            Shot(At("z_pond_bank"), 24f, 9f, null, 32f, 0.6f);
            yield return Wait(0.8f);
            yield return HeroWalk("z_pond_bank", 6f);   // 웅덩이 끝에 섬 → 끝 사건은 이 장면이 끝날 때(sceneEnd) 시작(QA P0-4)
            HeroFace("pond");
            yield return Wait(0.6f);
        }

        // 끝 — 대화9 「우리→가다→안」: 둘 다 끈을 맨 채 나란히 걸어 들어감(표정만 대화8 결과)
        IEnumerator sc_end_two()
        {
            var kid = N("kinopio");
            G.player.Stop();
            Shot(At("z_pond_bank"), 22f, 10f, null, 32f, 0.8f);
            if (kid) { kid.gameObject.SetActive(true); kid.StopFollow(); yield return Walk("kinopio", HeroSide(0.9f, 0f), true, 6f); kid.LookAt(At("pond")); }
            var surf = PondSurf(); if (surf) surf.Bulge(1f);
            AudioHub.Music(""); AudioHub.StopLoop("crowd", 1.5f);
            yield return Wait(1.2f);
            var into = Vector3.Lerp(At("z_pond_bank"), At("pond"), 0.35f);
            if (kid) kid.WalkTo(into + Hero.right * 0.9f);
            yield return HeroWalk(into, 5f);
            if (kid) kid.LookAt(Hero.position);
            yield return Wait(0.6f);
        }

        // 끝 — 떠안음: 물고기 입이 주인공 위로 닫히는 순간 키노피오가 스스로 뛰어듦(삼킴 장면 안에서 곁으로)
        IEnumerator sc_end_jump()
        {
            var kid = N("kinopio");
            G.player.Stop();
            if (kid) { kid.StopFollow(); kid.Warp(Hero.position - Hero.forward * 3.0f); kid.LookAt(Hero.position); }
            Shot(At("z_pond_bank"), 22f, 11f, null, 32f, 0.8f);
            var surf = PondSurf(); if (surf) surf.Bulge(1f);
            AudioHub.Music(""); AudioHub.StopLoop("crowd", 1.5f);
            yield return Wait(1.6f);
            if (kid) { Clip(kid, "RunAway"); AudioHub.Play("kid_run", 0.45f); yield return Walk("kinopio", HeroSide(0.8f, 0f), true, 3f); kid.LookAt(Hero.position); }
        }

        // 끝 — 물이 부풀어 오름(따짐: 줄 짚기 / 함께: 손 끌어당기기 전)
        IEnumerator sc_end_rise()
        {
            G.player.Stop();
            Shot(At("pond"), 22f, 18f, null, 34f, 1.2f);
            var surf = PondSurf(); if (surf) surf.Bulge(1f);
            AudioHub.Music(""); AudioHub.StopLoop("crowd", 1.5f);
            yield return Wait(1.6f);
            var kid = N("kinopio");
            if (kid && Has("f_d8_together"))
            {
                kid.StopFollow();
                Shot(Vector3.Lerp(Hero.position, kid.transform.position, 0.5f), 18f, 5f, null, 30f, 0.6f);
                kid.LookAt(At("pond")); kid.SetPose(ProceduralRig.Pose.Cower);   // 움찔 손을 빼려 함
                yield return Wait(1.0f);
                Pulse("pz_pull", 3f);
            }
            if (kid && Has("f_d8_accuse"))
            {
                // 주민 틈의 파란 반짝임(배지) 또는 긴 코끝 — 코끝만 줄 밖으로 삐죽(QA P1-11)
                Nose(kid, 5f);
                kid.LookAt(Hero.position); kid.SetPose(ProceduralRig.Pose.Stand);
                Shot(At("z_pond_lineup"), 30f, 14f, null, 36f, 0.6f);
                if (Has("f_badge")) AudioHub.Play("confirm", 0.3f, 1.6f);
                yield return Wait(1.2f);
            }
        }

        // 끝 — 따짐: 짚힌 키노피오가 뛰쳐나와 달려옴
        IEnumerator sc_end_kid_runs()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            Shot(Vector3.Lerp(Hero.position, kid.transform.position, 0.5f), 22f, 10f, null, 32f, 0.6f);
            kid.SetPose(ProceduralRig.Pose.Stand);
            kid.LookAt(Hero.position);
            yield return Wait(0.6f);
            Clip(kid, "RunAway"); AudioHub.Play("kid_run", 0.45f);
            yield return Walk("kinopio", HeroSide(0.8f, 0f), true, 6f);
            kid.LookAt(Hero.position);
            HeroFace("kinopio");
            yield return Wait(0.6f);
        }

        // 끝 — 함께: 물고기가 솟자 키노피오가 손을 빼려 함 → 주인공이 끌어당김
        IEnumerator sc_end_pull()
        {
            var kid = N("kinopio"); if (!kid) yield break;
            HeroPose("push");
            yield return Walk("kinopio", HeroSide(0.6f, 0f), true, 3f);
            HeroPose("stand");
            kid.LookAt(Hero.position); kid.SetPose(ProceduralRig.Pose.Stand);
            Prop("kid_hand", "hidden");
            yield return Wait(0.6f);
        }

        // 끝 — 삼킴(컷 2분 중 삼킴). 물고기가 둘을 삼키고 가라앉음. 웅덩이 위로 덩어리도 띠도 떠오르지 않음. 주민들이 오래 기다림
        IEnumerator sc_swallow()
        {
            var kid = N("kinopio");
            if (kid) { kid.gameObject.SetActive(true); kid.StopFollow(); if (Vector3.Distance(kid.transform.position, Hero.position) > 1.6f) yield return Walk("kinopio", HeroSide(0.8f, 0f), true, 5f); }
            Shot(At("pond"), 28f, 20f, null, 34f, 1f);
            yield return Wait(1.2f);
            Shot(Hero.position, -12f, 9f, null, 44f, 3f);   // 아래에서 위로 본 컷
            yield return Wait(0.6f);
            if (fish) yield return fish.Swallow(Hero, kid ? kid.transform : null);
            else { HeroVisible(false); if (kid) kid.gameObject.SetActive(false); }
            Shot(At("pond"), 24f, 18f, null, 34f, 0.6f);
            foreach (var n in G.AllNpcs.Where(x => x && x.npcId != "kinopio" && x.npcId != "fish" && x.gameObject.activeInHierarchy)) { n.LookAt(At("pond")); if (!Has("f_d9_up")) n.SetPose(ProceduralRig.Pose.Prostrate); else n.SetPose(ProceduralRig.Pose.LookUp); }
            yield return Wait(3.6f);   // 아무것도 떠오르지 않음 — 오래 기다림
            yield return G.ui.FadeOutRoutine(1.4f);
        }

        // 끝 — 뱃속(컷 1분): 어둠. 차곡차곡 쌓인 사람 물건, 의자에 놓이기를 기다리는 덩어리들, 붉은 끈 뭉치, 말린 띠 더미. 저 안쪽에서 종이 위로 붓 긋는 소리.
        // 키노피오가(대화8에 따라 미안한/뾰로통한/신난 얼굴) 소매를 쥠. 배지를 줬으면 그 빛만 보임. 끝. — 그림은 메인요청(ShowBellyDark에 얹을 것)
        IEnumerator sc_belly()
        {
            G.ui.ShowBellyDark();
            AudioHub.Music("music_ending");
            yield return Wait(1.6f);
            for (int i = 0; i < 4; i++) { AudioHub.Play("quill", 0.35f, 0.8f + i * 0.03f); yield return Wait(0.9f); }
            if (Has("f_badge")) AudioHub.Play("confirm", 0.25f, 1.4f);
            yield return Wait(2.4f);
        }

        IEnumerator sc_chapter_card()
        {
            G.ui.ShowChapterTitle("1장 끝", "물고기 뱃속으로");
            yield return Wait(4.4f);
        }

        PondSurface PondSurf() => PropState.All.TryGetValue("pond", out var p) ? p.GetComponentInChildren<PondSurface>() : null;

        // ═════════ 이야기 반응 rx_* — 대화 응답·사건이 부름(docs/반응목록.md §2) ═════════

        // ── 주인공 ──
        IEnumerator rx_hero_inspect() { HeroPose("crouch"); yield return Wait(1.0f); HeroPose("stand"); }
        IEnumerator rx_hero_squeeze_stuck()
        {
            var from = Hero.position;
            yield return HeroWalk(At("z_fall_gap"), 3f);
            yield return HeroClipWait("Squeeze", 1.4f);
            HeroPose("push_stuck"); AudioHub.Play("wrong", 0.4f, 1.2f);
            yield return Wait(1.2f);
            HeroPose("stand");
            yield return HeroWalk(from, 3f);
        }
        IEnumerator rx_hero_eat_grimace() { HeroPose("nod"); AudioHub.Play("piece", 0.3f, 0.6f); yield return Wait(0.9f); HeroPose("tilt"); yield return Wait(0.9f); HeroPose("stand"); }
        IEnumerator rx_hero_blocked_branches() { HeroPose("push"); yield return Wait(0.9f); HeroPose("tilt"); yield return Wait(0.6f); HeroPose("stand"); }
        IEnumerator rx_hero_blocked_soft() { HeroPose("tilt"); yield return Wait(0.7f); HeroPose("stand"); }

        // ── 수거꾼 우두머리 ──
        IEnumerator rx_collector_drop_sack_bow(NpcActor n)
        {
            AudioHub.Play("sack", 0.5f, 0.9f); Clack(3);
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Prostrate);
            yield return Wait(0.5f);
            foreach (var c in Grp("collectors")) c.SetPose(ProceduralRig.Pose.Prostrate);
            AudioHub.Play("crowd_bow", 0.5f);
            yield return Wait(1.2f);
        }
        IEnumerator rx_collector_scan_then_bow(NpcActor n)
        {
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.LookUp); yield return Wait(0.7f);
            n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(0.8f);
            n.SetPose(ProceduralRig.Pose.Prostrate);
            foreach (var c in Grp("collectors")) c.SetPose(ProceduralRig.Pose.Prostrate);
            yield return Wait(1.0f);
        }
        IEnumerator rx_collector_recoil_flee(NpcActor n)
        {
            var home = n.transform.position;
            n.LookAt(At("pond")); yield return Wait(0.3f);   // 겁: 한 번 웅덩이(밭) 쪽을 흘끗
            n.LookAt(Hero.position);
            float len = Clip(n, "Recoil"); n.SetPose(ProceduralRig.Pose.Cower);
            AudioHub.Play("wrong", 0.4f, 0.7f);
            n.WalkTo(home + (home - Hero.position).normalized * 2.0f);
            foreach (var c in Grp("collectors")) c.WalkTo(c.transform.position + (c.transform.position - Hero.position).normalized * 3f);
            yield return Wait(Mathf.Max(1.6f, len));
            yield return Wait(1.0f);   // 아무도 뒤따르지 않자
            n.SetPose(ProceduralRig.Pose.Stand);
            yield return Walk(n.npcId, home, true, 4f);   // 슬금슬금 돌아옴
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.HalfProstrate);
        }
        IEnumerator rx_collector_open_sack(NpcActor n) { n.LookAt(At("sack")); AudioHub.Play("sack", 0.7f, 1.1f); yield return ClipWait(n, "Grab", 1.2f); Prop("sack", "open"); n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_collector_look_around(NpcActor n) { n.SetPose(ProceduralRig.Pose.Stand); for (int i = 0; i < 3; i++) { n.LookAt(n.transform.position + Quaternion.Euler(0, i * 120f, 0) * Vector3.forward * 3f); yield return Wait(0.6f); } n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(0.8f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_collector_tilt(NpcActor n) { n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(1.1f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_boss_bow(NpcActor n) { n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.HalfProstrate); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_boss_tilt(NpcActor n) { n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(1.1f); n.SetPose(ProceduralRig.Pose.Kneel); }
        IEnumerator rx_boss_bow_spoon(NpcActor n)
        {
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Prostrate); AudioHub.Play("drop", 0.4f, 0.8f);
            yield return Wait(1.0f);
            n.SetPose(ProceduralRig.Pose.Stand);
            yield return ClipWait(n, "Offer", 1.5f);
            Prop("hero_spoon", "shown");
            AudioHub.Play("piece", 0.4f, 1.6f);
            n.SetPose(ProceduralRig.Pose.Prostrate);
            yield return Wait(0.6f);
        }
        IEnumerator rx_boss_step_aside(NpcActor n)
        {
            n.SetPose(ProceduralRig.Pose.Still); yield return Wait(1.0f);
            n.SetPose(ProceduralRig.Pose.Stand);
            yield return Walk(n.npcId, n.transform.position + Vector3.Cross(Vector3.up, (Hero.position - n.transform.position).normalized) * 1.6f, true, 3f);
            n.LookAt(Hero.position);
        }
        IEnumerator rx_boss_bag_on_head(NpcActor n)
        {
            n.SetPose(ProceduralRig.Pose.Stand);
            n.LookAt(At("z_cart")); yield return ClipWait(n, "Grab", 1.2f);   // 가방을 들려다 끈이 걸림
            AudioHub.Play("rope", 0.4f, 1.4f);
            yield return Walk(n.npcId, HeroSide(0f, 0.9f), true, 3f);
            n.LookAt(Hero.position); yield return ClipWait(n, "Offer", 1.5f);   // 주인공 머리 위에 두 손을 얹음(의식)
            n.SetPose(ProceduralRig.Pose.Kneel);
        }
        IEnumerator rx_boss_push_bag_deeper(NpcActor n) { n.LookAt(At("z_cart")); n.SetPose(ProceduralRig.Pose.Push); AudioHub.Play("drop", 0.3f, 1.2f); yield return Wait(1.2f); n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Kneel); yield return Wait(0.4f); }
        IEnumerator rx_boss_look_bag_hero_cart(NpcActor n) { n.LookAt(At("z_cart")); yield return Wait(0.7f); n.LookAt(Hero.position); yield return Wait(0.7f); n.LookAt(At("z_cart_lock")); yield return Wait(0.7f); n.LookAt(Hero.position); }

        // ── 키노피오 ──
        IEnumerator rx_kid_grin_hidenose(NpcActor n) { n.LookAt(Hero.position); Giggle(0.3f, 0.9f); yield return ClipWait(n, "Grin", 1.4f); Nose(n, noseGrow + 0.5f); yield return ClipWait(n, "HideNose", 0.6f); Resume(n); }
        IEnumerator rx_kid_laugh_tap_hero(NpcActor n) { Giggle(0.7f, 1.15f); yield return ClipWait(n, "Grin", 1.4f); yield return ClipWait(n, "Grin", 1.4f); n.LookAt(Hero.position); yield return ClipWait(n, "PointOther", 1.2f); Resume(n); }
        IEnumerator rx_kid_facepalm(NpcActor n) { yield return ClipWait(n, "HideNose", 0.6f); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(0.9f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_kid_tap_hero_chest(NpcActor n)
        {
            if (Vector3.Distance(n.transform.position, Hero.position) > 1.6f) yield return Walk("kinopio", HeroSide(0.7f, 0.7f), true, 3f);
            n.LookAt(Hero.position); G.ui.ShowGestureHint("other"); yield return ClipWait(n, "PointOther", 1.2f); Resume(n);
        }
        IEnumerator rx_kid_beckon(NpcActor n) { n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Beckon); yield return Wait(1.1f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_kid_tilt(NpcActor n) { n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); Resume(n); }
        IEnumerator rx_kid_blink_laugh_squeeze(NpcActor n) { n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Still); yield return Wait(0.6f); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.5f); Giggle(0.7f, 1.1f); yield return ClipWait(n, "Grin", 1.4f); }
        IEnumerator rx_kid_pull_hero_out(NpcActor n)
        {
            yield return Wait(2.2f);   // 주인공이 틈에 끼어 버둥(also: hero_squeeze_stuck)
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Reach); AudioHub.Play("rope", 0.3f, 1.6f);
            yield return Wait(1.0f);
            n.SetPose(ProceduralRig.Pose.Stand);
            yield return ClipWait(n, "Grin", 1.4f);
        }
        IEnumerator rx_kid_jump_look(NpcActor n) { n.SetPose(ProceduralRig.Pose.PointUp); AudioHub.Play("drop", 0.3f, 1.8f); yield return Wait(0.8f); n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(0.8f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_kid_walk_off_tilt(NpcActor n)
        {
            var home = n.transform.position;
            yield return Walk(n.npcId, home + (At("z_fall_bolt") - home).normalized * 2.0f, true, 3f);
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(0.9f); n.SetPose(ProceduralRig.Pose.Stand);
            yield return Walk(n.npcId, home, true, 3f); n.LookAt(Hero.position);
        }
        IEnumerator rx_kid_head_in_gap(NpcActor n) { n.LookAt(At("z_fall_gap")); n.SetPose(ProceduralRig.Pose.Push); yield return Wait(0.7f); n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position); yield return ClipWait(n, "PointSelf", 1.2f); }
        IEnumerator rx_kid_hide_behind_hero(NpcActor n) { yield return Walk("kinopio", HeroSide(0f, -0.9f), true, 3f); n.LookAt(At("chief")); n.SetPose(ProceduralRig.Pose.Cower); yield return Wait(0.8f); n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position); yield return ClipWait(n, "PointOther", 1.2f); }
        IEnumerator rx_kid_tap_chest_bow(NpcActor n) { yield return rx_kid_tap_hero_chest(n); n.LookAt(At("chief")); n.SetPose(ProceduralRig.Pose.HalfProstrate); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_kid_eat_all_drag(NpcActor n)
        {
            yield return Wait(1.6f);   // 그릇 든 주민들이 몰려온 뒤
            n.StopFollow();
            yield return Walk("kinopio", HeroSide(0.6f, 0.8f), true, 3f);
            n.SetPose(ProceduralRig.Pose.Gather); for (int i = 0; i < 3; i++) { AudioHub.Play("piece", 0.35f, 1.5f + i * 0.1f); yield return Wait(0.35f); }
            n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.6f);   // 볼이 빵빵
            n.SetPose(ProceduralRig.Pose.Stand);
            yield return ClipWait(n, "TugSleeve", 1.0f);
            yield return HeroWalk(Hero.position + (Hero.position - At("z_porridge")).normalized * 3f, 3f);
            Resume(n);
        }
        IEnumerator rx_kid_cover_laugh(NpcActor n) { yield return Wait(1.0f); Giggle(0.3f, 0.9f); yield return ClipWait(n, "HideNose", 0.6f); yield return ClipWait(n, "Grin", 1.4f); Resume(n); }
        IEnumerator rx_kid_right_pot(NpcActor n) { n.StopFollow(); yield return Walk("kinopio", At("z_porridge"), true, 4f); n.SetPose(ProceduralRig.Pose.Gather); AudioHub.Play("drop", 0.3f, 1.2f); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); Resume(n); }
        IEnumerator rx_kid_poke_strap(NpcActor n) { yield return Walk("kinopio", At("z_cart_lock") + new Vector3(0.6f, 0, 0.4f), true, 3f); n.LookAt(At("z_cart_lock")); n.SetPose(ProceduralRig.Pose.Reach); yield return Wait(0.5f); AudioHub.Play("hook_scrape", 0.3f, 1.5f); n.SetPose(ProceduralRig.Pose.HalfProstrate); yield return Wait(0.7f); n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position); }
        IEnumerator rx_kid_line_to_hole(NpcActor n)
        {
            n.LookAt(At("wall_drawing")); n.SetPose(ProceduralRig.Pose.Still); yield return Wait(1.2f);   // 오래 봄
            n.SetPose(ProceduralRig.Pose.Gather); for (int i = 0; i < 4; i++) { AudioHub.Play("quill", 0.4f, 0.9f + i * 0.08f); yield return Wait(0.3f); }
            Prop("wall_drawing", "line");
            n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position); yield return ClipWait(n, "Grin", 1.4f);
        }
        IEnumerator rx_kid_shake_hands(NpcActor n) { yield return Walk("kinopio", HeroSide(0.3f, 0.7f), true, 3f); n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Reach); HeroPose("reach"); for (int i = 0; i < 3; i++) { AudioHub.Play("piece", 0.3f, 1.3f); yield return Wait(0.3f); } HeroPose("stand"); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.8f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_kid_smudge_face(NpcActor n) { n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.8f); n.LookAt(At("wall_drawing")); n.SetPose(ProceduralRig.Pose.Reach); AudioHub.Play("quill", 0.35f, 0.6f); yield return Wait(1.0f); Prop("wall_drawing", "smudge"); n.SetPose(ProceduralRig.Pose.Stand); yield return Wait(0.6f); }
        IEnumerator rx_kid_freeze_fiddle(NpcActor n) { n.SetPose(ProceduralRig.Pose.Still); yield return Wait(1.2f); yield return Walk("kinopio", At("music_box") + new Vector3(-0.5f, 0, -0.4f), true, 3f); n.LookAt(At("music_box")); n.SetPose(ProceduralRig.Pose.Push); AudioHub.Play("musicbox_plink", 0.4f); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(At("wall_drawing")); n.SetPose(ProceduralRig.Pose.Point); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_kid_cover_mouth_smile(NpcActor n) { yield return Walk("kinopio", HeroSide(0.3f, 0.6f), true, 3f); n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Reach); yield return Wait(0.8f); n.LookAt(At("z_hideout_talk") + Vector3.left * 3f); yield return Wait(0.8f); n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Stand); yield return ClipWait(n, "Grin", 1.4f); }
        IEnumerator rx_kid_point_bro_hole(NpcActor n) { n.LookAt(At("wall_drawing")); n.SetPose(ProceduralRig.Pose.Point); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.PointUp); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position); }
        // 4-1 문 너머(키노피오는 문 안쪽 — 소리와 문 위주, 문이 열리는 모습은 sc_confession)
        IEnumerator rx_kid_door_open_bowed(NpcActor n) { yield return Wait(1.8f); AudioHub.Play("curtain", 0.35f, 0.5f); yield return Wait(0.6f); }
        IEnumerator rx_kid_door_burst_knot(NpcActor n) { AudioHub.Play("drop", 0.5f, 1.4f); yield return Wait(0.3f); AudioHub.Play("curtain", 0.6f, 1.3f); yield return Wait(0.6f); }
        IEnumerator rx_kid_door_slow_musicbox(NpcActor n) { AudioHub.Play("musicbox_plink", 0.45f); yield return Wait(1.4f); AudioHub.Play("curtain", 0.35f, 0.6f); yield return Wait(0.6f); }
        IEnumerator rx_kid_nose_withdraw(NpcActor n) { Shot(At("bark_door"), 16f, 3.5f, null, 28f, 0.9f); AudioHub.Play("piece", 0.3f, 1.2f); yield return Wait(1.6f); EndShot(); }   // 옹이 속 코끝이 쏙 들어감
        IEnumerator rx_kid_door_silent(NpcActor n) { yield return Wait(1.4f); }
        IEnumerator rx_kid_musicbox_click(NpcActor n) { AudioHub.Play("musicbox_plink", 0.5f); yield return Wait(0.8f); G.ui.ShowStageLine("s_we", "문 너머"); yield return Wait(2.0f); G.ui.ShowStageLine(null, null); }   // 문 너머 「우리」 한 글자

        // ── 촌장 ──
        IEnumerator rx_chief_kneel_tie(NpcActor n)
        {
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Kneel); AudioHub.Play("drop", 0.9f, 0.6f); G.ui.Shake(0.25f);
            yield return Wait(0.6f);
            HeroFace("chief");
            float len = Clip(n, "TieCord");
            yield return Wait(len > 0f ? Mathf.Min(1.36f, len) : 1.2f);
            Prop("hero_cord", "once"); AudioHub.Play("rope", 0.6f);
            yield return Wait(len > 1.36f ? len - 1.36f : 0.6f);
            foreach (var id in new[] { "gate_a", "gate_b" }) Pose(id, "prostrate");
            foreach (var c in Grp("crowd_gate")) c.SetPose(ProceduralRig.Pose.Prostrate);
            AudioHub.Play("crowd_bow", 0.6f); Clack(5);
            n.SetPose(ProceduralRig.Pose.Kneel);
            yield return Wait(0.8f);
        }
        IEnumerator rx_chief_tie_twice(NpcActor n)
        {
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Still); yield return Wait(1.6f);   // 오래 내려다봄
            float len = Clip(n, "TieCord");
            yield return Wait(len > 0f ? Mathf.Min(1.36f, len) : 1.2f);
            AudioHub.Play("rope", 0.6f); Prop("hero_cord", "twice"); yield return Wait(0.4f); AudioHub.Play("rope", 0.6f, 0.9f);
            yield return Wait(len > 1.36f ? len - 1.36f : 0.6f);
            n.SetPose(ProceduralRig.Pose.Point);   // 지킴이를 붙임(사건이 보이게 함)
            yield return Wait(0.8f);
            n.SetPose(ProceduralRig.Pose.Stand);
        }
        IEnumerator rx_chief_nod_wait(NpcActor n) { n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.8f); n.SetPose(ProceduralRig.Pose.Stand); for (int i = 0; i < 2; i++) { n.LookAt(n.transform.position + Quaternion.Euler(0, -60 + i * 120f, 0) * n.transform.forward * 4f); yield return Wait(0.7f); } n.LookAt(Hero.position); }
        IEnumerator rx_chief_branches_shake(NpcActor n)
        {
            n.LookAt(At("pond")); yield return Wait(0.3f);   // 웅덩이 쪽을 흘끗
            n.SetPose(ProceduralRig.Pose.Cower); Clack(6); G.ui.Shake(0.3f);
            foreach (var c in Grp("crowd_gate")) c.WalkTo(c.transform.position + (c.transform.position - Hero.position).normalized * 2.5f);
            yield return Wait(1.6f);
            n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position);
        }
        IEnumerator rx_chief_stare_kid(NpcActor n) { n.LookAt(At("kinopio")); n.SetPose(ProceduralRig.Pose.Still); yield return Wait(2.0f); n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position); }
        IEnumerator rx_chief_kneel_rooted(NpcActor n)
        {
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Kneel); AudioHub.Play("drop", 0.9f, 0.55f); G.ui.Shake(0.25f);
            yield return Wait(0.8f);
            foreach (var c in G.AllNpcs.Where(x => x && x.npcId != "kinopio" && x.npcId != "chief" && x.npcId != "fish" && x.gameObject.activeInHierarchy && Vector3.Distance(x.transform.position, Hero.position) < 15f)) c.SetPose(ProceduralRig.Pose.Prostrate);
            AudioHub.Play("crowd_bow", 0.7f);
            yield return Wait(1.2f);
        }
        IEnumerator rx_chief_bow_open(NpcActor n)
        {
            n.SetPose(ProceduralRig.Pose.HalfProstrate); yield return Wait(0.8f);
            var w = N("watcher");
            if (w && Has("f_d3_watch")) { w.LookAt(Hero.position); w.SetPose(ProceduralRig.Pose.Reach); yield return Wait(0.6f); w.SetPose(ProceduralRig.Pose.Stand); AudioHub.Play("rope", 0.4f, 1.3f); }   // 끈 끝을 놓아 줌
            yield return Wait(0.6f);
        }
        IEnumerator rx_chief_tie_kid(NpcActor n)
        {
            n.SetPose(ProceduralRig.Pose.Still);
            for (int i = 0; i < 3; i++) { n.LookAt(n.transform.position + Quaternion.Euler(0, -70 + i * 70f, 0) * n.transform.forward * 5f); yield return Wait(0.6f); }   // 줄을 훑어 키노피오를 찾음
            AudioHub.Loop("crowd", "crowd_murmur", 0.6f);   // 웅성(잠깐 크게)
            var kid = N("kinopio");
            if (kid)
            {
                kid.gameObject.SetActive(true); kid.StopFollow();
                if (Vector3.Distance(kid.transform.position, Hero.position) > 2f) { kid.SetPose(ProceduralRig.Pose.Stand); yield return Walk("kinopio", HeroSide(1.0f, 0.6f), true, 6f); }   // 어디 있든 불려 나옴
                n.LookAt(kid.transform.position);
                float len = Clip(n, "TieCord");
                yield return Wait(len > 0f ? len : 1.4f);
                Prop("kid_cord", "shown"); AudioHub.Play("rope", 0.6f);
                kid.LookAt(Hero.position);
            }
            AudioHub.Loop("crowd", "crowd_murmur", 0.4f);
            n.SetPose(ProceduralRig.Pose.Stand);
        }
        IEnumerator rx_chief_look_up_all(NpcActor n)
        {
            var hole = lightShaft ? lightShaft.position : At("fall");
            n.SetPose(ProceduralRig.Pose.LookUp); yield return Wait(0.8f);
            foreach (var c in G.AllNpcs.Where(x => x && x.npcId != "fish" && x.gameObject.activeInHierarchy && Vector3.Distance(x.transform.position, Hero.position) < 18f)) { c.SetPose(ProceduralRig.Pose.LookUp); c.LookAt(hole); }
            yield return Wait(1.6f);
        }
        IEnumerator rx_chief_turn_some_leave(NpcActor n)
        {
            n.LookAt(At("pond")); yield return Wait(0.8f);   // 등을 돌림
            var leavers = Grp("crowd_alley").Take(2).ToList();
            foreach (var c in leavers) { c.SetPose(ProceduralRig.Pose.Stand); c.WalkTo(At("z_cart_procession")); }
            yield return Wait(1.4f);
            n.LookAt(Hero.position);
        }
        IEnumerator rx_chief_staff_tap(NpcActor n) { n.LookAt(At("z_pond_bank")); n.SetPose(ProceduralRig.Pose.Point); AudioHub.Play("drop", 0.5f, 0.5f); yield return Wait(1.2f); n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position); }

        // ── 죽 주는 이 ──
        IEnumerator rx_porridge_bell_crowd(NpcActor n)
        {
            yield return Wait(1.0f);   // 주인공이 먹는 동안
            n.SetPose(ProceduralRig.Pose.Nod);
            for (int i = 0; i < 2; i++) { AudioHub.Play("bell_near", 0.35f, 2.1f); yield return Wait(0.25f); }   // 작은 손종
            AudioHub.Loop("crowd", "crowd_murmur", 0.4f);
            foreach (var c in Grp("crowd_plaza")) { c.SetPose(ProceduralRig.Pose.Stand); c.WalkTo(Hero.position + new Vector3(Random.Range(-2.2f, 2.2f), 0, Random.Range(-2.2f, 2.2f))); }
            var a = N("plaza_a"); if (a) { a.SetPose(ProceduralRig.Pose.Stand); a.WalkTo(HeroSide(-1.2f, 1.0f)); }
            yield return Wait(1.6f);
            if (a) Clip(a, "Offer");
            foreach (var c in Grp("crowd_plaza")) c.LookAt(Hero.position);
            yield return Wait(1.2f);
            AudioHub.StopLoop("crowd", 3f);
            n.SetPose(ProceduralRig.Pose.Stand);
        }
        IEnumerator rx_porridge_spoonfeed(NpcActor n) { yield return Walk(n.npcId, HeroSide(0f, 0.8f), true, 3f); n.LookAt(Hero.position); yield return ClipWait(n, "Offer", 1.5f); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.8f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_porridge_eat_follow(NpcActor n) { n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(0.7f); n.SetPose(ProceduralRig.Pose.Gather); AudioHub.Play("piece", 0.3f, 0.8f); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.8f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_porridge_drop_flee(NpcActor n)
        {
            n.LookAt(At("pond")); yield return Wait(0.3f);   // 웅덩이 쪽을 흘끗
            float len = Clip(n, "Recoil"); AudioHub.Play("drop", 0.7f, 0.9f);
            yield return Wait(Mathf.Max(0.6f, len));
            n.SetPose(ProceduralRig.Pose.Stand);
            yield return Walk(n.npcId, "z_back_corner", true, 4f);
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Cower);
            yield return Wait(0.6f);
        }
        IEnumerator rx_porridge_ladle_alternate(NpcActor n) { n.LookAt(Hero.position); Clip(n, "Offer"); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.6f); n.LookAt(Hero.position); Clip(n, "Offer"); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_porridge_tilt(NpcActor n) { n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_porridge_offer_again(NpcActor n) { n.LookAt(Hero.position); yield return ClipWait(n, "Offer", 1.5f); n.SetPose(ProceduralRig.Pose.Stand); }

        // ── 어미 · 주민 ──
        IEnumerator rx_mother_sigh_carry(NpcActor n)
        {
            n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(1.0f);   // 크게 숨을 내쉼
            n.SetPose(ProceduralRig.Pose.Stand); Prop("lump_spat", "hidden");
            yield return Walk(n.npcId, At("z_pond_stop"), true, 4f);   // 덩어리를 골목 의자로 모셔 감
            n.Warp(At("z_lump")); n.SetPose(ProceduralRig.Pose.Wipe);
        }
        IEnumerator rx_mother_freeze_flee(NpcActor n)
        {
            n.SetPose(ProceduralRig.Pose.Still); yield return Wait(1.4f);
            Prop("lump_spat", "hidden");
            n.SetPose(ProceduralRig.Pose.Stand);
            yield return Walk(n.npcId, At("z_pond_stop") + new Vector3(-3f, 0, 2f), true, 4f);
            n.Warp(At("z_lump"));   // 창문 너머 덩어리와 앉아 있음
        }
        IEnumerator rx_mother_brow_lump(NpcActor n) { n.LookAt(At("z_lump_spat")); n.SetPose(ProceduralRig.Pose.Prostrate); yield return Wait(1.6f); n.SetPose(ProceduralRig.Pose.Kneel); }
        IEnumerator rx_mother_cord_compare(NpcActor n)
        {
            n.LookAt(At("z_lump_spat")); yield return Wait(0.8f);
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(0.9f);
            n.LookAt(At("z_lump_spat")); yield return Wait(0.6f);
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Reach); yield return Wait(1.0f);   // 볼을 쓰다듬음
            n.SetPose(ProceduralRig.Pose.Stand);
            yield return Walk(n.npcId, At("z_pond_stop") + new Vector3(-3f, 0, 2f), true, 4f);   // 말없이 감(덩어리는 남김)
        }
        IEnumerator rx_mother_nod_offer(NpcActor n) { n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.8f); n.SetPose(ProceduralRig.Pose.Reach); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Kneel); }
        IEnumerator rx_mother_push_lump(NpcActor n) { n.SetPose(ProceduralRig.Pose.Reach); yield return Wait(1.2f); n.SetPose(ProceduralRig.Pose.Kneel); }
        IEnumerator rx_mother_tilt(NpcActor n) { n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Kneel); }
        IEnumerator rx_villager_recoil(NpcActor n) { float len = Clip(n, "Recoil"); if (len <= 0f) n.SetPose(ProceduralRig.Pose.Cower); n.WalkTo(n.transform.position + (n.transform.position - Hero.position).normalized * 1.4f); yield return Wait(Mathf.Max(1.0f, len)); }
        IEnumerator rx_crowd_bow_deeper(NpcActor n) { foreach (var c in Crowds().Where(x => Vector3.Distance(x.transform.position, Hero.position) < 16f)) c.SetPose(ProceduralRig.Pose.Prostrate); Clack(5); yield return Wait(1.2f); }
        IEnumerator rx_crowd_bow_pond(NpcActor n) { foreach (var c in Crowds().Where(x => Vector3.Distance(x.transform.position, Hero.position) < 16f)) { c.LookAt(At("pond")); c.SetPose(ProceduralRig.Pose.Prostrate); } AudioHub.Play("crowd_bow", 0.5f); yield return Wait(1.2f); }

        // ── QA 1차 보강 반응 ──
        // 꺾기 시범(대화6 넛지): 숯으로 큰 아이에서 옆으로 긋다 아래로 꺾어 긋는 ㄱ자 선
        IEnumerator rx_kid_demo_bend(NpcActor n)
        {
            var wall = At("wall_drawing");
            var right = Vector3.Cross(Vector3.up, (wall - n.transform.position).normalized);
            yield return Walk(n.npcId, wall - (wall - n.transform.position).normalized * 0.6f, true, 3f);
            n.LookAt(wall); n.SetPose(ProceduralRig.Pose.Point);
            for (int i = 0; i < 3; i++) { AudioHub.Play("quill", 0.4f, 1.0f); yield return Wait(0.25f); }   // 옆으로
            yield return Walk(n.npcId, n.transform.position + right * 0.7f, true, 2f);
            n.LookAt(wall); n.SetPose(ProceduralRig.Pose.Gather);
            for (int i = 0; i < 3; i++) { AudioHub.Play("quill", 0.4f, 0.8f); yield return Wait(0.25f); }   // 아래로 꺾어
            n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position);
            yield return ClipWait(n, "Grin", 1.4f);
        }
        // 꺾기 시범(대화8 넛지, 문 너머): 옹이의 코끝이 옆으로 갔다 아래로 + 껍질 긁는 소리
        IEnumerator rx_kid_demo_bend_door(NpcActor n)
        {
            Shot(At("bark_door"), 14f, 3.0f, null, 28f, 1.0f);
            Prop("door_nose", "short");
            for (int i = 0; i < 3; i++) { AudioHub.Play("hook_scrape", 0.25f, 1.6f); yield return Wait(0.3f); }
            yield return Wait(0.3f);
            for (int i = 0; i < 3; i++) { AudioHub.Play("hook_scrape", 0.25f, 1.3f); yield return Wait(0.3f); }
            yield return Wait(0.6f);
            EndShot();
        }
        IEnumerator rx_kid_tap_self_then_hero(NpcActor n)
        {
            if (Vector3.Distance(n.transform.position, Hero.position) > 1.6f) yield return Walk("kinopio", HeroSide(0.7f, 0.7f), true, 3f);
            n.LookAt(Hero.position);
            G.ui.ShowGestureHint("both");
            yield return ClipWait(n, "PointSelf", 1.2f);
            yield return ClipWait(n, "PointOther", 1.2f);
            Resume(n);
        }
        // 숨기기 놀이
        IEnumerator rx_kid_hide_bird(NpcActor n)
        {
            Giggle();
            HeroFace(Hero.position - (n.transform.position - Hero.position));   // 주인공이 등을 돌림
            yield return Wait(0.4f);
            yield return G.ui.FadeOutRoutine(0.5f);
            n.Warp(At("hide_nest") + new Vector3(0.5f, 0, -0.5f)); AudioHub.Play("sack", 0.3f, 1.4f);
            yield return Wait(0.6f);
            n.Warp(At("z_hideout_talk") + new Vector3(1.2f, 0, 0.4f));
            yield return G.ui.FadeIn(0.5f);
            n.LookAt(Hero.position); Giggle(0.4f, 0.9f);
            yield return ClipWait(n, "HideNose", 0.6f);   // 입을 막고 킥킥
        }
        IEnumerator rx_kid_give_bird(NpcActor n)
        {
            yield return Walk("kinopio", HeroSide(0.5f, 0.6f), true, 3f);
            n.LookAt(Hero.position); yield return ClipWait(n, "Reach", 1.2f);   // 나무 새를 내 손에
            HeroPose("hug"); yield return Wait(0.6f); HeroPose("stand");
            n.LookAt(n.transform.position - (Hero.position - n.transform.position)); yield return ClipWait(n, "HideNose", 0.6f);   // 돌아서 눈을 가림
            Giggle(0.4f, 0.9f);
        }
        IEnumerator rx_kid_hide_together(NpcActor n) { n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Nod); Giggle(); yield return Wait(0.8f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_kid_into_nest(NpcActor n) { yield return Walk("kinopio", At("hide_nest") + new Vector3(0.3f, 0, -0.3f), true, 3f); n.SetPose(ProceduralRig.Pose.Sit); Giggle(); yield return Wait(1.2f); n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position); }
        IEnumerator rx_kid_point_stash_lips(NpcActor n) { n.LookAt(At("stash")); n.SetPose(ProceduralRig.Pose.Point); yield return Wait(0.9f); n.LookAt(Hero.position); yield return ClipWait(n, "HideNose", 0.6f); }
        IEnumerator rx_kid_giggle_hidden(NpcActor n) { Giggle(0.45f, 0.95f); yield return Wait(0.4f); }   // 다른 자리 — 어디선가 킥킥
        // 골라서 하는 대화 — 주민
        IEnumerator rx_villager_tilt(NpcActor n) { n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_villager_prostrate_quick(NpcActor n) { n.SetPose(ProceduralRig.Pose.Prostrate); Clack(2); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_villager_bow_inward_stone(NpcActor n)
        {
            var inner = AreaSystem.I != null && AreaSystem.I.ExitToward(At("plaza")) is AreaExit ex ? Game.Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y)) : At("z_chief_gate");
            n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(inner); n.SetPose(ProceduralRig.Pose.Prostrate); Clack(3);
            yield return Wait(1.2f);
            n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(At("gate_stone")); n.SetPose(ProceduralRig.Pose.Point);
            Pulse("ins_gate", 2.5f);
            yield return Wait(1.2f);
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Stand);
        }
        IEnumerator rx_villager_point_stone_nod(NpcActor n) { n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(At("gate_stone")); n.SetPose(ProceduralRig.Pose.Point); Pulse("ins_gate", 2.5f); yield return Wait(1.2f); n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(1.0f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_villager_bow_with_crowd(NpcActor n)
        {
            n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Prostrate);
            foreach (var c in Crowds().Where(x => Vector3.Distance(x.transform.position, Hero.position) < 14f)) { c.LookAt(Hero.position); c.SetPose(ProceduralRig.Pose.Prostrate); }
            AudioHub.Play("crowd_bow", 0.6f); Clack(6);
            yield return Wait(1.6f);
        }
        IEnumerator rx_villager_panic_bow_back(NpcActor n)
        {
            float len = Clip(n, "Recoil"); yield return Wait(Mathf.Max(0.6f, len));
            n.SetPose(ProceduralRig.Pose.Prostrate); Clack(4);
            foreach (var c in Crowds().Where(x => Vector3.Distance(x.transform.position, Hero.position) < 14f)) { c.SetPose(ProceduralRig.Pose.Cower); }
            yield return Wait(1.0f);
            foreach (var c in Crowds().Where(x => Vector3.Distance(x.transform.position, Hero.position) < 14f)) c.SetPose(ProceduralRig.Pose.Prostrate);
            yield return Wait(0.8f);
        }
        IEnumerator rx_fieldkid_nod_hard_pulled(NpcActor n)
        {
            n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position);
            for (int i = 0; i < 3; i++) { n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.35f); }
            n.LookAt(At("pond")); n.SetPose(ProceduralRig.Pose.Point); yield return Wait(1.0f);
            var e = N("field_elder"); if (e) { e.SetPose(ProceduralRig.Pose.Stand); e.LookAt(n.transform.position); e.SetPose(ProceduralRig.Pose.Reach); }
            yield return Wait(0.8f);
            n.WalkTo(n.transform.position + (e ? (e.transform.position - n.transform.position).normalized * 0.6f : Vector3.zero));
            n.SetPose(ProceduralRig.Pose.Prostrate); if (e) e.SetPose(ProceduralRig.Pose.Prostrate);
            yield return Wait(0.8f);
        }
        IEnumerator rx_fieldkid_mime_swallow(NpcActor n) { n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.PointUp); yield return Wait(0.6f); n.SetPose(ProceduralRig.Pose.Hug); AudioHub.Play("fish_gulp", 0.25f, 1.6f); yield return Wait(0.9f); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.6f); n.SetPose(ProceduralRig.Pose.Stand); }
        IEnumerator rx_fieldkid_look_elder(NpcActor n) { n.LookAt(At("field_elder")); yield return Wait(0.7f); n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Tilt); yield return Wait(0.9f); n.SetPose(ProceduralRig.Pose.Stand); }
        // 이웃(창 안 — 걷지 않음)
        IEnumerator rx_neighbor_nod_hook(NpcActor n) { n.LookAt(Hero.position); n.SetPose(ProceduralRig.Pose.Nod); yield return Wait(0.8f); n.LookAt(At("cord_hook")); n.SetPose(ProceduralRig.Pose.Reach); yield return Wait(1.2f); n.LookAt(At("bark_door")); n.SetPose(ProceduralRig.Pose.Stand); yield return Wait(0.8f); n.LookAt(Hero.position); }
        IEnumerator rx_neighbor_freeze_bow(NpcActor n) { n.SetPose(ProceduralRig.Pose.Still); yield return Wait(1.2f); n.LookAt(At("brother_lump")); n.SetPose(ProceduralRig.Pose.HalfProstrate); yield return Wait(1.4f); n.SetPose(ProceduralRig.Pose.Stand); n.LookAt(Hero.position); }
        IEnumerator rx_neighbor_recoil(NpcActor n) { float len = Clip(n, "Recoil"); if (len <= 0f) n.SetPose(ProceduralRig.Pose.Cower); yield return Wait(Mathf.Max(1.0f, len)); n.SetPose(ProceduralRig.Pose.Stand); }
    }
}
