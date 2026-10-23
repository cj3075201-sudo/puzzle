using UnityEngine;

namespace OUAT.World
{
    /// <summary>장소 구역(fall, gate, plaza …). 들어가면 "enter:장소" 사건을 알린다.</summary>
    [RequireComponent(typeof(Collider))]
    public class PlaceZone : MonoBehaviour
    {
        public string placeId;
        public static event System.Action<string> Entered;
        public static event System.Action<string> Exited;
        public static string Current { get; private set; }

        void Reset() { GetComponent<Collider>().isTrigger = true; }

        void OnTriggerEnter(Collider other)
        {
            if (!other.GetComponentInParent<PlayerMover>()) return;
            Current = placeId;
            Entered?.Invoke(placeId);
        }

        void OnTriggerExit(Collider other)
        {
            if (!other.GetComponentInParent<PlayerMover>()) return;
            Exited?.Invoke(placeId);
        }
    }
}
