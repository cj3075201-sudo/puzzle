using System.Collections;
using OUAT.Core;
using UnityEngine;

namespace OUAT.World
{
    /// <summary>
    /// 장치 퍼즐(사다리 걸쇠·바퀴 고정쇠의 가방 끈·오르골·손 끌어당기기). 데이터 puzzles[].host 물건에 붙는다. 사람 물건은 주인공만 다룬다(크리처는 자격이 없음).
    /// 누르면 손을 뻗어 잠깐 붙잡고(데이터 interaction "hold:초") 풀린다. 그려진 빗장(drawnBolt)과 짚기(pick)는 사건이 맡는다.
    /// </summary>
    public class PuzzleObject : MonoBehaviour
    {
        public string puzzleId;
        [Tooltip("풀렸을 때 움직일 부분(걸쇠 손잡이 등)")] public Transform movingPart;
        public Vector3 openedLocalEuler = new Vector3(0, 0, -95);
        public Vector3 openedLocalOffset = new Vector3(0, 0.05f, 0);
        [Tooltip("풀리면 사라질 막힘")] public GameObject blocker;

        public bool Solved { get; private set; }
        Vector3 closedEuler, closedPos;
        bool busy;

        void Awake()
        {
            if (movingPart) { closedEuler = movingPart.localEulerAngles; closedPos = movingPart.localPosition; }
        }

        public void Use()
        {
            if (Solved || busy) return;
            var g = Game.I;
            if (!g.Data.Puzzles.TryGetValue(puzzleId, out var def)) return;
            if (def.Type == "drawnBolt" || def.Type == "pick") return;
            g.StartCoroutine(HoldRoutine(def));
        }

        IEnumerator HoldRoutine(PuzzleDef def)
        {
            var g = Game.I;
            busy = true; g.Busy = true;
            float hold = 1.2f;
            var inter = J.Str(def.Raw, "interaction");
            if (inter.StartsWith("hold:") && float.TryParse(inter.Substring(5), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var h)) hold = h;
            var rig = g.player.GetComponentInChildren<ProceduralRig>();
            var spot = GetComponentInChildren<Interactable>(true);   // 누르는 자리(Use_ 트리거, 예: 수레 바퀴 고정쇠) 쪽을 봄
            g.player.Face(spot ? spot.transform.position : transform.position);
            if (rig) rig.SetPose(ProceduralRig.Pose.Reach);
            g.ui.ShowHold(true);
            float t = 0;
            while (t < hold)
            {
                t += Time.deltaTime;
                g.ui.SetHoldProgress(t / hold);
                if (movingPart) movingPart.localPosition = closedPos + Random.insideUnitSphere * 0.006f;
                yield return null;
            }
            g.ui.ShowHold(false);
            if (rig) rig.SetPose(ProceduralRig.Pose.Stand);
            yield return SolveRoutine(def);
            busy = false; g.Busy = false;
        }

        IEnumerator SolveRoutine(PuzzleDef def)
        {
            var game = Game.I;
            Solved = true;
            if (movingPart)
            {
                float t = 0;
                var fromR = movingPart.localRotation; var toR = Quaternion.Euler(closedEuler + openedLocalEuler);
                var fromP = movingPart.localPosition; var toP = closedPos + openedLocalOffset;
                while (t < 1f)
                {
                    t += Time.deltaTime * 2.4f;
                    float k = 1f - Mathf.Pow(1f - Mathf.Clamp01(t), 3f);
                    movingPart.localRotation = Quaternion.Slerp(fromR, toR, k);
                    movingPart.localPosition = Vector3.Lerp(fromP, toP, k);
                    yield return null;
                }
            }
            AudioHub.Play("latch");
            if (blocker) blocker.SetActive(false);
            foreach (var f in def.Set) game.State.Set(f);
            game.State.Set("puzzle:" + puzzleId);
            GetComponentInChildren<Interactable>(true)?.SetAvailable(false);
            game.Fire("puzzle:" + puzzleId);
            game.Save();
        }

        public void SetState(string s)
        {
            if (s == "solved" || s == "open")
            {
                Solved = true;
                if (movingPart) { movingPart.localEulerAngles = closedEuler + openedLocalEuler; movingPart.localPosition = closedPos + openedLocalOffset; }
                if (blocker) blocker.SetActive(false);
                GetComponentInChildren<Interactable>(true)?.SetAvailable(false);
            }
        }

        public void Reapply(GameState s) { if (s.Has("puzzle:" + puzzleId)) SetState("solved"); }
    }
}
