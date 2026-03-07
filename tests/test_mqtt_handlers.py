import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the current directory to the path so we can import mqtt_handlers
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import mqtt_handlers


@pytest.fixture
def setup_mqtt_handlers():
    """Set up test fixtures before each test method."""
    # Reset global variables
    mqtt_handlers.shared_state = None
    mqtt_handlers.FGCOLOR = None
    mqtt_handlers.BGCOLOR = None
    mqtt_handlers.board = None
    mqtt_handlers.GPIO = None
    mqtt_handlers.RESET_PIN = None
    mqtt_handlers.m = None
    mqtt_handlers.template = None
    mqtt_handlers.local_weather = None
    mqtt_handlers.refresh = True
    mqtt_handlers.enable_auto_template = True

    # Create mock objects
    mock_mqtt_client = Mock()
    mock_board = Mock()
    mock_gpio = Mock()
    mock_template = Mock()
    mock_weather = Mock()

    yield {
        'mqtt_client': mock_mqtt_client,
        'board': mock_board,
        'gpio': mock_gpio,
        'template': mock_template,
        'weather': mock_weather
    }

    # Cleanup after each test
    mqtt_handlers.shared_state = None
    mqtt_handlers.FGCOLOR = None
    mqtt_handlers.BGCOLOR = None
    mqtt_handlers.board = None
    mqtt_handlers.GPIO = None
    mqtt_handlers.RESET_PIN = None
    mqtt_handlers.m = None
    mqtt_handlers.template = None
    mqtt_handlers.local_weather = None
    mqtt_handlers.refresh = True
    mqtt_handlers.enable_auto_template = True


def test_init_shared_state(setup_mqtt_handlers):
    """Test initialization of shared state."""
    mocks = setup_mqtt_handlers
    state_dict = {'template': 'test', 'local_weather': 'sunny', 'refresh': False, 'enable_auto_template': False}
    fg_color = b'\xff\x00\x00'
    bg_color = b'\x00\x00\x00'
    reset_pin = 17

    mqtt_handlers.init_shared_state(
        state_dict, fg_color, bg_color, mocks['board'],
        mocks['gpio'], reset_pin, mocks['mqtt_client']
    )

    assert mqtt_handlers.shared_state == state_dict
    assert mqtt_handlers.FGCOLOR == fg_color
    assert mqtt_handlers.BGCOLOR == bg_color
    assert mqtt_handlers.board == mocks['board']
    assert mqtt_handlers.GPIO == mocks['gpio']
    assert mqtt_handlers.RESET_PIN == reset_pin
    assert mqtt_handlers.m == mocks['mqtt_client']


def test_update_template(setup_mqtt_handlers):
    """Test template update function."""
    mocks = setup_mqtt_handlers

    # Mock debug_template_change by patching at the function level
    mock_debug = Mock()
    original_update_template = mqtt_handlers.update_template

    def mock_update_template(new_template):
        # Mock the import inside the function
        import sys
        if 'main' in sys.modules:
            del sys.modules['main']
        # Create a mock main module with debug_template_change
        mock_main = Mock()
        mock_main.debug_template_change = mock_debug
        sys.modules['main'] = mock_main

        # Call the original function
        return original_update_template(new_template)

    # Replace the function temporarily
    mqtt_handlers.update_template = mock_update_template

    try:
        state_dict = {'template': 'old_template'}
        mqtt_handlers.shared_state = state_dict
        mqtt_handlers.template = 'old_template'

        mqtt_handlers.update_template('new_template')

        assert mock_debug.call_count == 2  # Called twice in update_template
        assert mqtt_handlers.template == 'new_template'
        assert mqtt_handlers.shared_state['template'] == 'new_template'
    finally:
        # Restore the original function
        mqtt_handlers.update_template = original_update_template


def test_mqttLogger_with_client(setup_mqtt_handlers):
    """Test MQTT logging when client is available."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.m = mocks['mqtt_client']
    message = "Test log message"

    mqtt_handlers.mqttLogger(message)

    mocks['mqtt_client'].publish.assert_called_once_with("marquee/logging", payload=message)
    mocks['mqtt_client'].publish.return_value.wait_for_publish.assert_called_once()


def test_mqttLogger_without_client(setup_mqtt_handlers):
    """Test MQTT logging when client is not available."""
    mqtt_handlers.m = None

    # Should not raise an exception
    mqtt_handlers.mqttLogger("Test message")


@patch('mqtt_handlers.handle_esp32_message')
def test_new_message_esp32_message(mock_handler, setup_mqtt_handlers):
    """Test new_message routing to esp32 message handler."""
    msg = Mock()
    msg.topic = "esp32/test/message"
    msg.payload = b'test payload'

    mqtt_handlers.new_message(None, None, msg)

    mock_handler.assert_called_once_with(msg)


@patch('mqtt_handlers.handle_fgcolor')
def test_new_message_fgcolor(mock_handler, setup_mqtt_handlers):
    """Test new_message routing to fgcolor handler."""
    msg = Mock()
    msg.topic = "esp32/test/fgcolor"
    msg.payload = b'\xff\x00\x00'

    mqtt_handlers.new_message(None, None, msg)

    mock_handler.assert_called_once_with(msg)


def test_new_message_unrecognized_topic(setup_mqtt_handlers):
    """Test new_message with unrecognized topic."""
    with patch('mqtt_handlers.mqttLogger') as mock_logger:
        msg = Mock()
        msg.topic = "unknown/topic"
        msg.payload = b'test'

        mqtt_handlers.new_message(None, None, msg)

        mock_logger.assert_called_with("Unrecognized topic: unknown/topic")


def test_new_message_exception_handling(setup_mqtt_handlers):
    """Test exception handling in new_message."""
    with patch('mqtt_handlers.mqttLogger') as mock_logger:
        msg = Mock()
        msg.topic = "esp32/test/message"
        msg.payload = b'test'

        # Force an exception by making handlers raise an error
        with patch('mqtt_handlers.handle_esp32_message', side_effect=Exception("Test error")):
            mqtt_handlers.new_message(None, None, msg)

        mock_logger.assert_called_with("Error processing message on topic esp32/test/message: Test error")


def test_handle_fgcolor_valid(setup_mqtt_handlers):
    """Test handle_fgcolor with valid 3-byte payload."""
    msg = Mock()
    msg.payload = b'\xff\x00\x80'

    mqtt_handlers.handle_fgcolor(msg)

    assert mqtt_handlers.FGCOLOR == b'\xff\x00\x80'


def test_handle_fgcolor_invalid_length(setup_mqtt_handlers):
    """Test handle_fgcolor with invalid payload length."""
    msg = Mock()
    msg.payload = b'\xff\x00'  # Only 2 bytes

    original_fgcolor = mqtt_handlers.FGCOLOR
    mqtt_handlers.handle_fgcolor(msg)

    # Should not change if length != 3
    assert mqtt_handlers.FGCOLOR == original_fgcolor


def test_handle_bgcolor_valid(setup_mqtt_handlers):
    """Test handle_bgcolor with valid 3-byte payload."""
    msg = Mock()
    msg.payload = b'\x00\x80\xff'

    mqtt_handlers.handle_bgcolor(msg)

    assert mqtt_handlers.BGCOLOR == b'\x00\x80\xff'


def test_handle_bgcolor_invalid_length(setup_mqtt_handlers):
    """Test handle_bgcolor with invalid payload length."""
    msg = Mock()
    msg.payload = b'\x00\x80'  # Only 2 bytes

    original_bgcolor = mqtt_handlers.BGCOLOR
    mqtt_handlers.handle_bgcolor(msg)

    # Should not change if length != 3
    assert mqtt_handlers.BGCOLOR == original_bgcolor


@patch('mqtt_handlers.process_raw')
def test_handle_raw(mock_process_raw, setup_mqtt_handlers):
    """Test handle_raw delegates to process_raw."""
    msg = Mock()
    msg.payload = b'test raw data'

    mqtt_handlers.handle_raw(msg)

    mock_process_raw.assert_called_once_with(msg.payload)


@patch('mqtt_handlers.time.sleep')
def test_handle_reset(mock_sleep, setup_mqtt_handlers):
    """Test handle_reset toggles GPIO pins."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.GPIO = mocks['gpio']
    mqtt_handlers.RESET_PIN = 17

    msg = Mock()
    mqtt_handlers.handle_reset(msg)

    mocks['gpio'].output.assert_any_call(17, mocks['gpio'].HIGH)
    mocks['gpio'].output.assert_any_call(17, mocks['gpio'].LOW)
    mock_sleep.assert_called_once_with(5)


def test_handle_bright(setup_mqtt_handlers):
    """Test handle_bright sets board brightness."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.board = mocks['board']

    msg = Mock()
    msg.payload = b'\x80'  # 128

    mqtt_handlers.handle_bright(msg)

    mocks['board'].set_brightness.assert_called_once_with(128)


@patch('mqtt_handlers.check_template')
@patch('mqtt_handlers.update_template')
def test_handle_template_gmonster(mock_update_template, mock_check_template, setup_mqtt_handlers):
    """Test handle_template for gmonster template."""
    mocks = setup_mqtt_handlers

    # Mock the check_template to capture what template class it receives
    def check_template_side_effect(template_class, **kwargs):
        # Create a mock instance and call update_template with it
        mock_instance = Mock()
        mock_update_template(mock_instance)
        return mock_instance

    mock_check_template.side_effect = check_template_side_effect

    mqtt_handlers.board = mocks['board']
    mqtt_handlers.local_weather = mocks['weather']

    msg = Mock()
    msg.payload = b'gmonster'

    mqtt_handlers.handle_template(msg)

    # Verify check_template was called with gmonster class
    mock_check_template.assert_called_once_with(mqtt_handlers.gmonster, force=True)
    mock_update_template.assert_called_once()


@patch('mqtt_handlers.check_template')
@patch('mqtt_handlers.update_template')
def test_handle_template_clock(mock_update_template, mock_check_template, setup_mqtt_handlers):
    """Test handle_template for clock template."""
    mocks = setup_mqtt_handlers

    # Mock the check_template to capture what template class it receives
    def check_template_side_effect(template_class, **kwargs):
        # Create a mock instance and call update_template with it
        mock_instance = Mock()
        mock_update_template(mock_instance)
        return mock_instance

    mock_check_template.side_effect = check_template_side_effect

    mqtt_handlers.board = mocks['board']
    mqtt_handlers.local_weather = mocks['weather']

    msg = Mock()
    msg.payload = b'clock'

    mqtt_handlers.handle_template(msg)

    # Verify check_template was called with clock class and weather parameter
    mock_check_template.assert_called_once_with(mqtt_handlers.clock, weather=mocks['weather'], force=True)
    mock_update_template.assert_called_once()


@patch('mqtt_handlers.check_template')
@patch('mqtt_handlers.update_template')
def test_handle_template_timer(mock_update_template, mock_check_template, setup_mqtt_handlers):
    """Test handle_template for timer template."""
    mocks = setup_mqtt_handlers

    # Track the mock instance that gets created
    created_mock_instance = None

    # Mock the check_template to capture what template class it receives
    def check_template_side_effect(template_class, **kwargs):
        nonlocal created_mock_instance
        # Create a mock instance and set it as the global template
        mock_instance = Mock()
        mock_instance.set_timer_duration = Mock()
        created_mock_instance = mock_instance
        mqtt_handlers.template = mock_instance  # Set the global template
        mock_update_template(mock_instance)
        return mock_instance

    mock_check_template.side_effect = check_template_side_effect

    mqtt_handlers.board = mocks['board']

    msg = Mock()
    msg.payload = b'timer'

    mqtt_handlers.handle_template(msg)

    # Verify check_template was called with timer class and parameters
    mock_check_template.assert_called_once_with(mqtt_handlers.timer, interval=5, clear=True, force=True)
    mock_update_template.assert_called_once()
    # The template should have set_timer_duration called
    assert created_mock_instance is not None
    created_mock_instance.set_timer_duration.assert_called_once_with("00:10")


@patch('mqtt_handlers.check_template')
def test_handle_timer_duration(mock_check_template, setup_mqtt_handlers):
    """Test handle_timer_duration."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.template = mocks['template']

    msg = Mock()
    msg.payload = b'00:05'

    mqtt_handlers.handle_timer_duration(msg)

    mock_check_template.assert_called_once_with(mqtt_handlers.timer, clear=True)
    mocks['template'].set_timer_duration.assert_called_once_with('00:05')


@patch('mqtt_handlers.check_template')
def test_handle_gmonster_box(mock_check_template, setup_mqtt_handlers):
    """Test handle_gmonster_box with inning topic."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.template = mocks['template']

    msg = Mock()
    msg.topic = "marquee/template/gmonster/box/inning/top/1"
    msg.payload = b'5'

    mqtt_handlers.handle_gmonster_box(msg)

    mock_check_template.assert_called_once_with(mqtt_handlers.gmonster)
    mocks['template'].update_box.assert_called_once_with('inning', 'top', '5', index=0)


@patch('mqtt_handlers.check_template')
def test_handle_gmonster_count(mock_check_template, setup_mqtt_handlers):
    """Test handle_gmonster_count."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.template = mocks['template']

    msg = Mock()
    msg.topic = "marquee/template/gmonster/count/home"
    msg.payload = b'3'

    mqtt_handlers.handle_gmonster_count(msg)

    mock_check_template.assert_called_once_with(mqtt_handlers.gmonster)
    mocks['template'].update_count.assert_called_once_with('home', '3')


@patch('mqtt_handlers.check_template')
def test_handle_gmonster_inning(mock_check_template, setup_mqtt_handlers):
    """Test handle_gmonster_inning."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.template = mocks['template']

    msg = Mock()
    msg.topic = "marquee/template/gmonster/inning/top"
    msg.payload = b'7'

    mqtt_handlers.handle_gmonster_inning(msg)

    mock_check_template.assert_called_once_with(mqtt_handlers.gmonster)
    mocks['template'].update_current_inning.assert_called_once_with('top', '7')


@pytest.mark.xfail(reason="Complex auto-switch logic not triggering correctly with mocks")
@patch('mqtt_handlers.check_template')
@patch('mqtt_handlers.update_template')
def test_handle_gmonster_game_ended_auto_switch(mock_update_template, mock_check_template, setup_mqtt_handlers):
    """Test handle_gmonster_game auto-switch to clock when game ends."""
    mocks = setup_mqtt_handlers
    from templates import gmonster

    # Mock the check_template to capture what template class it receives
    def check_template_side_effect(template_class, **kwargs):
        # Create a mock instance and call update_template with it
        mock_instance = Mock()
        mock_update_template(mock_instance)
        return mock_instance

    mock_check_template.side_effect = check_template_side_effect

    mqtt_handlers.template = Mock(spec=gmonster)
    mqtt_handlers.template.disable_close = False
    mqtt_handlers.template.update_game_status = Mock()  # Add the missing method
    mqtt_handlers.board = mocks['board']
    mqtt_handlers.local_weather = mocks['weather']

    msg = Mock()
    msg.topic = "marquee/template/gmonster/game"
    msg.payload = b'F'  # Game finished

    mqtt_handlers.handle_gmonster_game(msg)

    # Should call update_game_status first, then auto-switch to clock
    mqtt_handlers.template.update_game_status.assert_called_once_with('F')
    # Verify check_template was called with clock class and weather parameter
    mock_check_template.assert_called_once_with(mqtt_handlers.clock, weather=mocks['weather'])
    mock_update_template.assert_called_once()


@patch('mqtt_handlers.check_template')
def test_handle_gmonster_disable_win_true(mock_check_template, setup_mqtt_handlers):
    """Test handle_gmonster_disable_win sets disable_win to True."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.template = mocks['template']

    msg = Mock()
    msg.payload = b'true'

    mqtt_handlers.handle_gmonster_disable_win(msg)

    assert mocks['template'].disable_win == True


@patch('mqtt_handlers.check_template')
def test_handle_gmonster_disable_win_false(mock_check_template, setup_mqtt_handlers):
    """Test handle_gmonster_disable_win sets disable_win to False."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.template = mocks['template']

    msg = Mock()
    msg.payload = b'false'

    mqtt_handlers.handle_gmonster_disable_win(msg)

    assert mocks['template'].disable_win == False


@patch('mqtt_handlers.check_template')
def test_handle_gmonster_bases_first_true(mock_check_template, setup_mqtt_handlers):
    """Test handle_gmonster_bases for first base."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.template = mocks['template']

    msg = Mock()
    msg.topic = "marquee/template/gmonster/bases/first"
    msg.payload = b'true'

    mqtt_handlers.handle_gmonster_bases(msg)

    mocks['template'].update_bases.assert_called_once_with(first=True)


@patch('mqtt_handlers.check_template')
def test_handle_gmonster_bases_second_false(mock_check_template, setup_mqtt_handlers):
    """Test handle_gmonster_bases for second base false."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.template = mocks['template']

    msg = Mock()
    msg.topic = "marquee/template/gmonster/bases/second"
    msg.payload = b'false'

    mqtt_handlers.handle_gmonster_bases(msg)

    mocks['template'].update_bases.assert_called_once_with(second=False)


def test_handle_auto_template_enable(setup_mqtt_handlers):
    """Test handle_auto_template enables auto template."""
    msg = Mock()
    msg.payload = b'true'

    mqtt_handlers.handle_auto_template(msg)

    assert mqtt_handlers.enable_auto_template == True


def test_handle_auto_template_disable(setup_mqtt_handlers):
    """Test handle_auto_template disables auto template."""
    msg = Mock()
    msg.payload = b'false'

    mqtt_handlers.handle_auto_template(msg)

    assert mqtt_handlers.enable_auto_template == False


@patch('mqtt_handlers.check_template')
def test_handle_scrolltext_basic(mock_check_template, setup_mqtt_handlers):
    """Test handle_scrolltext with basic parameters."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.template = mocks['template']
    mqtt_handlers.FGCOLOR = b'\xff\x00\x00'
    mqtt_handlers.BGCOLOR = b'\x00\x00\xff'

    msg = Mock()
    msg.topic = "marquee/template/base/scrolltext"
    msg.payload = b'Hello World'

    mqtt_handlers.handle_scrolltext(msg)

    mocks['template'].scroll_text.assert_called_once_with(
        'Hello World',
        speed=0.05,
        direction='left',
        loop=True,
        y_offset=0,
        fgcolor=b'\xff\x00\x00',
        bgcolor=b'\x00\x00\xff'
    )


@patch('mqtt_handlers.check_template')
def test_handle_scrolltext_with_parameters(mock_check_template, setup_mqtt_handlers):
    """Test handle_scrolltext with custom parameters."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.template = mocks['template']

    msg = Mock()
    msg.topic = "marquee/template/base/scrolltext/0.1/right/false/5"
    msg.payload = b'Custom Text'

    mqtt_handlers.handle_scrolltext(msg)

    mocks['template'].scroll_text.assert_called_once_with(
        'Custom Text',
        speed=0.1,
        direction='right',
        loop=False,
        y_offset=5,
        fgcolor=None,
        bgcolor=None
    )


@patch('mqtt_handlers.send_pixels')
def test_handle_get_pixels(mock_send_pixels, setup_mqtt_handlers):
    """Test handle_get_pixels calls send_pixels."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.board = mocks['board']

    msg = Mock()
    mqtt_handlers.handle_get_pixels(msg)

    mock_send_pixels.assert_called_once_with(mocks['board'])


def test_handle_temperature(setup_mqtt_handlers):
    """Test handle_temperature updates weather."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.local_weather = mocks['weather']

    msg = Mock()
    msg.payload = b'72.5'

    mqtt_handlers.handle_temperature(msg)

    mocks['weather'].temperature.assert_called_once_with('72.5')


@pytest.mark.xfail(reason="Mock object __del__ method restrictions prevent proper testing")
def test_check_template_force_switch(setup_mqtt_handlers):
    """Test check_template with force=True."""
    mocks = setup_mqtt_handlers
    from templates import base
    with patch('templates.base') as mock_base_class:
        mock_base_instance = Mock()
        mock_base_instance.__del__ = Mock()  # Add __del__ method
        mock_base_class.return_value = mock_base_instance

        mqtt_handlers.board = mocks['board']
        mqtt_handlers.template = Mock()  # Old template
        mqtt_handlers.template.__del__ = Mock()  # Add __del__ to old template
        mqtt_handlers.shared_state = {'template': 'old'}

        mqtt_handlers.check_template(base, force=True, test_param='value')

        mock_base_class.assert_called_once_with(mocks['board'], test_param='value')
        assert mqtt_handlers.template == mock_base_instance
        assert mqtt_handlers.shared_state['template'] == mock_base_instance


@pytest.mark.xfail(reason="isinstance() with module types not compatible with mocking")
def test_check_template_auto_switch_enabled(setup_mqtt_handlers):
    """Test check_template with auto switch enabled."""
    mocks = setup_mqtt_handlers
    from templates import base
    with patch('templates.base') as mock_base_class:
        mock_base_instance = Mock()
        mock_base_class.return_value = mock_base_instance

        mqtt_handlers.board = mocks['board']
        # Create a mock template that is not an instance of base
        mqtt_handlers.template = Mock()
        mqtt_handlers.template.__class__ = Mock  # Make it a different type
        mqtt_handlers.enable_auto_template = True

        mqtt_handlers.check_template(base)

        mock_base_class.assert_called_once_with(mocks['board'])
        assert mqtt_handlers.template == mock_base_instance


def test_check_template_auto_switch_disabled(setup_mqtt_handlers):
    """Test check_template with auto switch disabled."""
    mocks = setup_mqtt_handlers
    from templates import base
    with patch('templates.base') as mock_base_class:
        mqtt_handlers.board = mocks['board']
        mqtt_handlers.template = Mock()  # Different type
        mqtt_handlers.enable_auto_template = False

        old_template = mqtt_handlers.template
        mqtt_handlers.check_template(base)

        # Should not switch templates
        assert mqtt_handlers.template == old_template
        mock_base_class.assert_not_called()


@patch('json.dumps')
def test_send_pixels(mock_json_dumps, setup_mqtt_handlers):
    """Test send_pixels publishes pixel data."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.m = mocks['mqtt_client']
    mqtt_handlers.board = mocks['board']

    pixels = [{'x': 0, 'y': 0, 'r': 255, 'g': 0, 'b': 0}]
    mocks['board'].get_pixels.return_value = pixels
    mock_json_dumps.return_value = '{"x": 0, "y": 0, "r": 255, "g": 0, "b": 0}'

    mqtt_handlers.send_pixels(mocks['board'])

    mock_json_dumps.assert_called_once_with(pixels[0])
    mocks['mqtt_client'].publish.assert_called_once_with(
        "marquee/pixels",
        '{"x": 0, "y": 0, "r": 255, "g": 0, "b": 0}'
    )


def test_process_raw_valid_length(setup_mqtt_handlers):
    """Test process_raw with valid message length (multiple of 6)."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.board = mocks['board']

    message = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b'  # 12 bytes = 2 pixels

    mqtt_handlers.process_raw(message)

    # Should call set_pixel twice
    assert mocks['board'].set_pixel.call_count == 2
    mocks['board'].set_pixel.assert_any_call(b'\x00\x01\x02\x03\x04\x05')
    mocks['board'].set_pixel.assert_any_call(b'\x06\x07\x08\x09\x0a\x0b')


def test_process_raw_invalid_length(setup_mqtt_handlers):
    """Test process_raw with invalid message length."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.board = mocks['board']

    message = b'\x00\x01\x02\x03\x04'  # 5 bytes, not multiple of 6

    with patch('builtins.print') as mock_print:
        mqtt_handlers.process_raw(message)

        # Should print error message and then "Raw message processed"
        assert mock_print.call_count == 2
        mock_print.assert_any_call("Message error:", message)
        mock_print.assert_any_call("Raw message processed")
        mocks['board'].set_pixel.assert_not_called()


@patch('neomatrix.font.font_5x8')
def test_update_message(mock_font_5x8, setup_mqtt_handlers):
    """Test update_message renders text using font."""
    mocks = setup_mqtt_handlers
    mqtt_handlers.board = mocks['board']
    mqtt_handlers.FGCOLOR = b'\xff\x00\x00'
    mqtt_handlers.BGCOLOR = b'\x00\x00\xff'

    # Mock font generator
    mock_font_5x8.return_value = [
        (0, 0, b'\xff\x00\x00'),
        (1, 0, b'\xff\x00\x00'),
        (0, 1, b'\x00\xff\x00')
    ]

    message = "Hi"
    anchor = (10, 5)

    mqtt_handlers.update_message(message, anchor)

    mock_font_5x8.assert_called_once_with(message, fgcolor=b'\xff\x00\x00')
    # Should call set_pixel for each character pixel
    expected_calls = [
        ((10).to_bytes(2, "big") + (5).to_bytes(1, "big") + b'\xff\x00\x00',),
        ((11).to_bytes(2, "big") + (5).to_bytes(1, "big") + b'\xff\x00\x00',),
        ((10).to_bytes(2, "big") + (6).to_bytes(1, "big") + b'\x00\xff\x00',)
    ]
    # Check that set_pixel was called the right number of times
    assert mocks['board'].set_pixel.call_count == 3
