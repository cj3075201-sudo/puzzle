using System.Collections.Generic;
using UnityEngine;

namespace OUAT.World
{
    /// <summary>누를 수 있는 것: 크리처(npc), 새김(inscription), 장치(puzzle), 사람 물건(item), 그 밖(prop).</summary>
    public class Interactable : MonoBehaviour
    {
        public enum Kind { Npc, Inscription, Puzzle, Item, Prop }
        public Kind kind = Kind.Prop;
        public string id;
        [Tooltip("누르면 걸어갈 자리(없으면 대상 앞)")] public Transform approach;
        public float approachDistance = 1.4f;
        [Tooltip("지금 누를 수 있나(대화가 안 열린 크리처 등은 꺼 둠)")] public bool available = true;
        public string hoverLabel;

        public static readonly List<Interactable> All = new List<Interactable>();
        Renderer[] rends;
        MaterialPropertyBlock mpb;
        float highlight, highlightGoal, pulse;
        static readonly int HighlightId = Shader.PropertyToID("_Highlight");

        void OnEnable() { All.Add(this); }
        void OnDisable() { All.Remove(this); }

        void Awake() { rends = GetComponentsInChildren<Renderer>(); mpb = new MaterialPropertyBlock(); }

        public void RefreshRenderers() { rends = GetComponentsInChildren<Renderer>(); }

        public Vector3 ApproachPoint(Vector3 from)
        {
            if (approach) return approach.position;
            var dir = from - transform.position; dir.y = 0;
            if (dir.sqrMagnitude < 0.01f) dir = transform.forward;
            return transform.position + dir.normalized * approachDistance;
        }

        public void SetHover(bool on) { highlightGoal = on ? 1f : 0f; }
        public void SetAvailable(bool on) { available = on; if (!on) highlightGoal = 0f; }
        public void Pulse(float seconds = 1.6f) { pulse = Mathf.Max(pulse, seconds); }

        void Update()
        {
            pulse = Mathf.Max(0f, pulse - Time.deltaTime);
            float goal = Mathf.Max(highlightGoal, available ? Mathf.Clamp01(pulse) * (0.6f + 0.4f * Mathf.Sin(Time.time * 10f)) : 0f);
            if (Mathf.Approximately(goal, highlight)) return;
            highlight = Mathf.MoveTowards(highlight, goal, Time.deltaTime * 6f);
            foreach (var r in rends)
            {
                if (!r) continue;
                r.GetPropertyBlock(mpb);
                mpb.SetFloat(HighlightId, highlight);
                r.SetPropertyBlock(mpb);
            }
        }
    }
}
