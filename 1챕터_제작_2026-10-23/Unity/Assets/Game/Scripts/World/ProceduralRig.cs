using System.Collections.Generic;
using UnityEngine;

namespace OUAT.World
{
    /// <summary>
    /// 리깅 없는 부위 계층(Body/Head/ArmL/ArmR/WingL/WingR/LegL/LegR/Nose …)을 절차적으로 움직인다.
    /// 크리처(목각 인형)는 관절을 끊어 꺾듯 2~3단계로 딱딱 넘어가고(반응목록 공통 원칙), 파랑새는 부드럽게.
    /// 자세 이름은 데이터(docs/반응목록.md §1)의 pose id와 같다.
    /// </summary>
    public class ProceduralRig : MonoBehaviour
    {
        public enum Pose
        {
            Stand, Still, Sit, Prostrate, HalfProstrate, Kneel, Crouch, Cower,
            Point, PointUp, LookUp, Tilt, Nod, Hug, Push, PushStuck,
            Gather, Bury, Stack, LoadCart, Wipe, MarkKid, Prepare,
            FacePond, Seated, Reach,
            Beckon, LookBack, LieDown, GetUp, LookAround, Fall, Talk, Greet, Shout, Shrug,
            Bow = Prostrate, HalfBow = HalfProstrate
        }

        [Tooltip("걷는 속도(m/s). 바깥에서 매 프레임 넣어 준다.")] public float speed;
        public Pose pose = Pose.Stand;
        [Range(0.5f, 2f)] public float bobScale = 1f;
        public float breathe = 0.015f;
        public bool isBird;
        [Tooltip("목각 인형처럼 자세가 끊어져 넘어감")] public bool stepped = true;

        Transform root, body, head, armL, armR, legL, legR, nose;
        readonly Dictionary<Transform, Quaternion> rest = new Dictionary<Transform, Quaternion>();
        Vector3 rootRest, noseRestScale = Vector3.one;
        float walkPhase, poseBlend, timeOffset, noseFlicker;
        Pose shownPose = Pose.Stand;

        void Awake()
        {
            root = transform.childCount > 0 ? transform.GetChild(0) : transform;
            rootRest = root.localPosition;
            body = Find("Body"); head = Find("Head");
            armL = Find("ArmL") ?? Find("WingL"); armR = Find("ArmR") ?? Find("WingR");
            legL = Find("LegL"); legR = Find("LegR"); nose = Find("Nose");
            foreach (var t in new[] { body, head, armL, armR, legL, legR, nose })
                if (t != null) rest[t] = t.localRotation;
            if (nose) noseRestScale = nose.localScale;
            timeOffset = Random.value * 10f;
            if (isBird) stepped = false;
            anim = GetComponentInChildren<Animation>();
            if (anim != null && anim.GetClipCount() > 0) SetupClips(); else anim = null;
        }

        // ── 뼈대 애니메이션(블렌더 클립, Legacy Animation)이 있으면 그것으로 — 없으면 아래 절차 자세 ──
        Animation anim;
        string current;
        [Tooltip("Walk 클립이 발 미끄럼 없이 맞는 속도(m/s)")] public float walkClipSpeed = 1.4f;
        [Tooltip("Run 클립이 맞는 속도(m/s)")] public float runClipSpeed = 3.6f;
        public bool HasClips => anim != null;

        static readonly HashSet<string> Loops = new HashSet<string> { "Idle", "Walk", "Run", "Talk", "BowHold", "LookUp", "Gather", "SitIdle", "FallTumble", "LieDown", "Kneel", "StandSway", "Carry", "Crowd", "RunAway", "Sulk", "Proclaim" };

        void SetupClips()
        {
            // 블렌더 클립이 발 미끄럼 없이 맞는 속도(art/아트기준 §11): 주인공 3.2/5.0, 키노피오 2.2/4.0, 나머지 2.2
            var n = anim.gameObject.name;
            if (n.Contains("Hero")) { walkClipSpeed = 1.8f; runClipSpeed = 3.2f; }   // 사람 아이(1.25m): 걷기 1.8, 뛰기 3.2
            else if (n.Contains("Kinopio")) { walkClipSpeed = 2.2f; runClipSpeed = 4.0f; }
            else { walkClipSpeed = 2.2f; runClipSpeed = 4.0f; }
            foreach (var smr in GetComponentsInChildren<SkinnedMeshRenderer>(true)) smr.updateWhenOffscreen = true;   // 엎드림·쓰러짐이 경계 상자 밖으로 나가도 그림
            foreach (AnimationState s in anim)
            {
                s.wrapMode = Loops.Contains(s.name) ? WrapMode.Loop : WrapMode.ClampForever;
                if (s.name == "Walk" && walkClipSpeed <= 0) walkClipSpeed = 1.4f;
            }
            anim.playAutomatically = false;
            Play(Has("StandSway") ? "StandSway" : "Idle", 0f);
        }

        bool Has(string c) => anim != null && anim[c] != null;

        /// <summary>자세 표에 없는 클립(키노피오 FileNose·HideNose·Grin·TugSleeve, 촌장 TieCord 등)을 이름으로 한 번 재생. 끝나면 지금 자세로 돌아감.</summary>
        public float PlayClip(string clip, float fade = 0.15f)
        {
            if (!Has(clip)) return 0f;
            current = clip; oneShot = true;
            anim.CrossFade(clip, fade);
            anim[clip].time = 0f;
            if (!Loops.Contains(clip)) { CancelInvoke(nameof(BackToPose)); Invoke(nameof(BackToPose), anim[clip].length); }
            return anim[clip].length;
        }
        void BackToPose() { current = null; oneShot = false; }
        bool oneShot;

        void Play(string clip, float fade = 0.2f)
        {
            if (clip == null || clip == current || !Has(clip)) return;
            var prev = current; current = clip;
            // 엎드림 → 일어설 때는 Rise를 거쳐서
            if (prev == "BowHold" && clip != "Bow" && Has("Rise")) { anim.CrossFade("Rise", 0.15f); anim.CrossFadeQueued(clip, 0.25f, QueueMode.CompleteOthers); return; }
            if (prev == "LieDown" && clip != "GetUp" && Has("GetUp")) { anim.CrossFade("GetUp", 0.15f); anim.CrossFadeQueued(clip, 0.25f, QueueMode.CompleteOthers); return; }
            if (clip == "BowHold" && Has("Bow")) { anim.CrossFade("Bow", fade); anim.CrossFadeQueued("BowHold", 0.1f, QueueMode.CompleteOthers); return; }
            if (fade <= 0f) anim.Play(clip); else anim.CrossFade(clip, fade);
            anim[clip].time = 0f;
        }

        string ClipFor(Pose p)
        {
            string c = p switch
            {
                Pose.Stand or Pose.Still or Pose.FacePond => Has("StandSway") ? "StandSway" : "Idle",
                Pose.Sit or Pose.Seated => "SitIdle",
                Pose.Prostrate => "BowHold",
                Pose.HalfProstrate => Has("Greet") ? "Greet" : "BowHold",
                Pose.Kneel => "Kneel",
                Pose.Crouch or Pose.Gather or Pose.Bury or Pose.Stack or Pose.LoadCart or Pose.Wipe or Pose.MarkKid or Pose.Prepare => "Gather",
                Pose.Cower => "Cower",
                Pose.Point => "Point",
                Pose.PointUp => "PointUp",
                Pose.LookUp => "LookUp",
                Pose.Tilt => "HeadTilt",
                Pose.Nod => "Nod",
                Pose.Hug or Pose.Talk => "Talk",
                Pose.Push or Pose.PushStuck => "Push",
                Pose.Reach => "Reach",
                Pose.Beckon => "Beckon",
                Pose.LookBack => "LookBack",
                Pose.LieDown => "LieDown",
                Pose.GetUp => "GetUp",
                Pose.LookAround => "LookAround",
                Pose.Fall => "FallTumble",
                Pose.Greet => "Greet",
                Pose.Shout => "Shout",
                Pose.Shrug => "Shrug",
                _ => "Idle"
            };
            return Has(c) ? c : (Has("Kneel") && p == Pose.HalfProstrate ? "Kneel" : "Idle");
        }

        void ClipUpdate()
        {
            bool moving = speed > 0.2f;
            if (oneShot && !moving) return;   // 이름으로 부른 클립이 끝날 때까지
            if (oneShot && moving) { oneShot = false; CancelInvoke(nameof(BackToPose)); }
            if (moving)
            {
                bool run = Has("Run") && speed > (walkClipSpeed + runClipSpeed) * 0.5f;
                var c = run ? "Run" : "Walk";
                Play(c, 0.18f);
                if (Has(c)) anim[c].speed = Mathf.Clamp(speed / (run ? runClipSpeed : walkClipSpeed), 0.5f, 2f);
            }
            else Play(ClipFor(pose), 0.25f);
            if (nose)
            {
                noseFlicker = Mathf.MoveTowards(noseFlicker, 0f, Time.deltaTime * 5f);
                nose.localScale = NoseScale() * (1f + 0.07f * Mathf.Sin(noseFlicker * Mathf.PI));
            }
        }

        Transform Find(string n)
        {
            foreach (var t in GetComponentsInChildren<Transform>(true))
                if (t != transform && (t.name == n || t.name.StartsWith(n + ".") || t.name.EndsWith("_" + n))) return t;
            return null;
        }

        public void SetPose(Pose p) { pose = p; }

        /// <summary>코 선이 한 순간 아주 살짝 길어졌다 돌아옴(거짓말인지 밝히지 않는 떨림).</summary>
        public void FlickerNose() { noseFlicker = 1f; }

        /// <summary>키노피오 코 길이: 거짓말마다 늘고(1·2·3…), 갈면 0. 앞 방향 배율 = 1 + 0.18·g(부드럽게 따라감).</summary>
        public void SetNoseGrow(float g) { noseGrowGoal = Mathf.Max(0f, g); }
        float noseGrowGoal, noseGrow;
        Vector3 NoseScale()
        {
            noseGrow = Mathf.MoveTowards(noseGrow, noseGrowGoal, Time.deltaTime * 1.6f);
            var s = noseRestScale; float k = 1f + 0.18f * noseGrow;
            // 코의 긴 축(가장 큰 축)만 늘림
            if (s.z >= s.x && s.z >= s.y) s.z *= k; else if (s.y >= s.x) s.y *= k; else s.x *= k;
            return s;
        }

        public static Pose Parse(string s)
        {
            switch ((s ?? "").ToLowerInvariant())
            {
                case "still": case "watch": return Pose.Still;
                case "sit": return Pose.Sit;
                case "prostrate": case "bow": return Pose.Prostrate;
                case "half_prostrate": case "halfbow": return Pose.HalfProstrate;
                case "kneel": return Pose.Kneel;
                case "crouch": return Pose.Crouch;
                case "cower": return Pose.Cower;
                case "point": return Pose.Point;
                case "pointup": case "point_up": return Pose.PointUp;
                case "lookup": case "look_up": return Pose.LookUp;
                case "tilt": return Pose.Tilt;
                case "nod": return Pose.Nod;
                case "hug": return Pose.Hug;
                case "push": return Pose.Push;
                case "push_stuck": return Pose.PushStuck;
                case "gather": return Pose.Gather;
                case "bury": return Pose.Bury;
                case "stack": return Pose.Stack;
                case "load_cart": return Pose.LoadCart;
                case "wipe": return Pose.Wipe;
                case "mark_kid": return Pose.MarkKid;
                case "prepare": return Pose.Prepare;
                case "face_pond": return Pose.FacePond;
                case "seated": return Pose.Seated;
                case "reach": return Pose.Reach;
                case "beckon": return Pose.Beckon;
                case "look_back": return Pose.LookBack;
                case "lie_down": return Pose.LieDown;
                case "get_up": return Pose.GetUp;
                case "look_around": return Pose.LookAround;
                case "talk": return Pose.Talk;
                case "greet": return Pose.Greet;
                case "shout": return Pose.Shout;
                case "shrug": return Pose.Shrug;
                case "line_up": case "lead": case "follow": case "face_lump": case "rehearse": case "act": case "stand": default: return Pose.Stand;
            }
        }

        void LateUpdate()
        {
            if (anim != null) { ClipUpdate(); return; }
            float t = Time.time + timeOffset;
            float move = Mathf.Clamp01(speed / 2.2f);
            walkPhase += Time.deltaTime * Mathf.Lerp(0f, 9f, move) * (isBird ? 1.25f : 1f);
            if (shownPose != pose) { poseBlend = Mathf.MoveTowards(poseBlend, 0f, Time.deltaTime * 4f); if (poseBlend <= 0f) shownPose = pose; }
            else poseBlend = Mathf.MoveTowards(poseBlend, 1f, Time.deltaTime * 3.2f);
            float k = Smooth(poseBlend);
            if (stepped) k = Mathf.Round(k * 3f) / 3f;

            bool still = shownPose == Pose.Still;
            float bob = Mathf.Abs(Mathf.Sin(walkPhase)) * 0.06f * move * bobScale;
            float br = still ? 0f : Mathf.Sin(t * 1.6f) * breathe * (1f - move);
            Vector3 lp = rootRest + new Vector3(0, bob + br, 0);
            Quaternion rootRot = Quaternion.Euler(0, 0, Mathf.Sin(walkPhase) * 4f * move);

            float bodyPitch = 0, headPitch = 0, headRoll = 0, armLX = 0, armRX = 0, legBend = 0, drop = 0, armSpread = 0;
            float work = Mathf.Sin(t * 4.2f);
            switch (shownPose)
            {
                case Pose.Prostrate: bodyPitch = 62; headPitch = 22; drop = 0.22f; armLX = armRX = 70; legBend = 70; break;
                case Pose.HalfProstrate: bodyPitch = 30; headPitch = 10; drop = 0.06f; armLX = armRX = 25; break;
                case Pose.Kneel: bodyPitch = 12; headPitch = 18; drop = 0.3f; legBend = 85; armLX = armRX = 15; break;
                case Pose.Crouch: bodyPitch = 25; drop = 0.22f; legBend = 60; armLX = armRX = 35; headPitch = 15; break;
                case Pose.Cower: bodyPitch = 40; headPitch = 25; drop = 0.25f; legBend = 70; armLX = armRX = 75; break;
                case Pose.Sit: drop = 0.32f; legBend = 85; headPitch = 8; break;
                case Pose.Seated: drop = 0.1f; legBend = 80; break;
                case Pose.Point: armRX = -85; break;
                case Pose.PointUp: armRX = -165; headPitch = -32; break;
                case Pose.LookUp: headPitch = -38; bodyPitch = -6; break;
                case Pose.Push: bodyPitch = 25; armLX = armRX = -78; legBend = 20 + work * 6; break;
                case Pose.PushStuck: bodyPitch = 25 + work * 5; armLX = armRX = -78; legBend = 18; break;
                case Pose.Hug: bodyPitch = 20; armLX = armRX = -55; armSpread = -25; drop = 0.12f; break;
                case Pose.Tilt: headRoll = 22; break;
                case Pose.Nod: headPitch = Mathf.Sin(t * 6f) * 12f; break;
                case Pose.Gather: bodyPitch = 40; drop = 0.08f; armRX = -40 + work * 30; armLX = 20; headPitch = 10; break;
                case Pose.Bury: bodyPitch = 48; drop = 0.15f; legBend = 35; armLX = -30 + work * 35; armRX = -30 - work * 35; break;
                case Pose.Stack: bodyPitch = 35 + work * 10; armLX = armRX = -50 + work * 30; legBend = 20; break;
                case Pose.LoadCart: bodyPitch = 20; armLX = armRX = -70 + Mathf.Abs(work) * 40; break;
                case Pose.Wipe: bodyPitch = 22; armRX = -60; armSpread = work * 18; headPitch = 12; break;
                case Pose.MarkKid: bodyPitch = 18; armRX = -70 + work * 8; headPitch = 15; break;
                case Pose.Prepare: armLX = -40 + work * 15; armRX = -30 - work * 15; headPitch = 10; break;
                case Pose.FacePond: bodyPitch = -10; headPitch = 5; break;
                case Pose.Reach: armRX = -70; bodyPitch = 12; break;
                case Pose.Beckon: armRX = -70 + Mathf.Sin(t * 9f) * 25f; headRoll = 8; break;
                case Pose.LookBack: headRoll = 6; break;
                case Pose.LieDown: bodyPitch = 85; drop = 0.35f; armLX = armRX = 80; legBend = 10; break;
                case Pose.LookAround: headRoll = Mathf.Sin(t * 2.5f) * 18f; break;
                case Pose.Talk: armRX = -30 + work * 12; break;
                case Pose.Greet: bodyPitch = 35; headPitch = 15; drop = 0.08f; break;
            }
            bodyPitch *= k; headPitch *= k; headRoll *= k; armLX *= k; armRX *= k; legBend *= k; drop *= k; armSpread *= k;

            root.localPosition = lp - new Vector3(0, drop, 0);
            root.localRotation = rootRot;

            float swing = Mathf.Sin(walkPhase) * 28f * move;
            if (body) body.localRotation = rest[body] * Quaternion.Euler(bodyPitch, 0, 0);
            if (head)
            {
                float idle = still ? 0f : 1f;
                head.localRotation = rest[head] * Quaternion.Euler(headPitch + Mathf.Sin(t * 0.9f) * 2f * idle, Mathf.Sin(t * 0.37f) * 4f * idle, headRoll);
            }
            if (isBird)
            {
                float flap = Mathf.Sin(walkPhase * 2f) * 10f * move;
                if (armL) armL.localRotation = rest[armL] * Quaternion.Euler(armLX - swing * 0.4f, 0, 12f + flap + armSpread);
                if (armR) armR.localRotation = rest[armR] * Quaternion.Euler(armRX + swing * 0.4f, 0, -12f - flap - armSpread);
            }
            else
            {
                if (armL) armL.localRotation = rest[armL] * Quaternion.Euler(armLX - swing, 0, armSpread);
                if (armR) armR.localRotation = rest[armR] * Quaternion.Euler(armRX + swing, 0, -armSpread);
            }
            if (legL) legL.localRotation = rest[legL] * Quaternion.Euler(swing + legBend, 0, 0);
            if (legR) legR.localRotation = rest[legR] * Quaternion.Euler(-swing + legBend, 0, 0);
            if (nose)
            {
                nose.localRotation = rest[nose] * Quaternion.Euler(Mathf.Sin(t * 2.3f) * 1.5f, 0, 0);
                noseFlicker = Mathf.MoveTowards(noseFlicker, 0f, Time.deltaTime * 5f);
                nose.localScale = NoseScale() * (1f + 0.07f * Mathf.Sin(noseFlicker * Mathf.PI));
            }
        }

        static float Smooth(float x) => x * x * (3f - 2f * x);
    }
}
