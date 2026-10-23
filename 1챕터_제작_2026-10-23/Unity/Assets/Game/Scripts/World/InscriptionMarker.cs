using System.Collections.Generic;
using UnityEngine;

namespace OUAT.World
{
    /// <summary>새겨진 문장 자리. 다 맞게 읽어 낸 뒤에는 번역 문장이 그 자리에 남아 가까이 가면 보인다(뜻-28 ①).</summary>
    public class InscriptionMarker : MonoBehaviour
    {
        public string inscriptionId;
        public string sentenceId;
        public Transform labelAnchor;
        public bool Translated { get; private set; }
        public static readonly List<InscriptionMarker> All = new List<InscriptionMarker>();

        void OnEnable() { All.Add(this); }
        void OnDisable() { All.Remove(this); }

        public Vector3 LabelPosition => labelAnchor ? labelAnchor.position : transform.position + Vector3.up * 1.6f;
        public void ShowTranslation() { Translated = true; }
    }
}
