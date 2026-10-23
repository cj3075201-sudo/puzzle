using UnityEngine;

namespace OUAT.World
{
    /// <summary>들어가면 카메라 각도를 바꾸는 구역.</summary>
    [RequireComponent(typeof(Collider))]
    public class CameraZone : MonoBehaviour
    {
        public FollowCamera.View view = FollowCamera.View.Default;
        public int priority;

        void Reset() { GetComponent<Collider>().isTrigger = true; }

        void OnTriggerEnter(Collider other)
        {
            if (other.GetComponentInParent<PlayerMover>() && Camera.main && Camera.main.TryGetComponent<FollowCamera>(out var fc)) fc.Enter(this);
        }

        void OnTriggerExit(Collider other)
        {
            if (other.GetComponentInParent<PlayerMover>() && Camera.main && Camera.main.TryGetComponent<FollowCamera>(out var fc)) fc.Exit(this);
        }
    }
}
