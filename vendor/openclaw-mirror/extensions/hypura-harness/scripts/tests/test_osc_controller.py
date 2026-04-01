# scripts/hypura/tests/test_osc_controller.py
from unittest.mock import MagicMock, patch


def test_send_chatbox_calls_osc() -> None:
    with patch("osc_controller.udp_client.SimpleUDPClient") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        from osc_controller import OSCController

        ctrl = OSCController(host="127.0.0.1", port=9000)
        ctrl.send_chatbox("hello")
        mock_instance.send_message.assert_called_once_with(
            "/chatbox/input", ["hello", True, True]
        )


def test_set_param_sends_correct_address() -> None:
    with patch("osc_controller.udp_client.SimpleUDPClient") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        from osc_controller import OSCController

        ctrl = OSCController()
        ctrl.set_param("FaceEmotion", 1)
        mock_instance.send_message.assert_called_once_with(
            "/avatar/parameters/FaceEmotion", 1
        )


def test_apply_emotion_sends_multiple_params() -> None:
    with patch("osc_controller.udp_client.SimpleUDPClient") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        from osc_controller import OSCController, load_param_map

        param_map = load_param_map()
        ctrl = OSCController(param_map=param_map)
        ctrl.apply_emotion("happy")
        calls = [str(c) for c in mock_instance.send_message.call_args_list]
        assert any("FaceEmotion" in c for c in calls)
        assert any("SmileIntensity" in c for c in calls)


def test_apply_emotion_unknown_falls_back_to_neutral() -> None:
    with patch("osc_controller.udp_client.SimpleUDPClient") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        from osc_controller import OSCController, load_param_map

        ctrl = OSCController(param_map=load_param_map())
        ctrl.apply_emotion("confused")  # not in map
        assert mock_instance.send_message.called
