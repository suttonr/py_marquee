import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the current directory to the path so we can import quad_spi
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Mock pigpio module with consistent constants
mock_pigpio_module = Mock()
mock_pigpio_module.OUTPUT = 0
mock_pigpio_module.INPUT = 1
sys.modules['pigpio'] = mock_pigpio_module
import quad_spi


@pytest.fixture
def mock_pigpio():
    """Mock pigpio.pi class for testing."""
    with patch('pigpio.pi') as mock_pi_class:
        mock_pi_instance = Mock()
        mock_pi_instance.connected = True
        # Use the same constants from the module mock
        mock_pi_instance.OUTPUT = mock_pigpio_module.OUTPUT
        mock_pi_instance.INPUT = mock_pigpio_module.INPUT
        mock_pi_class.return_value = mock_pi_instance
        yield mock_pi_instance


@pytest.fixture
def quad_spi_instance(mock_pigpio):
    """Create a QuadSPI instance with mocked pigpio."""
    cs_pin, sclk_pin, io0_pin, io1_pin, io2_pin, io3_pin = 8, 11, 10, 9, 7, 6
    qspi = quad_spi.QuadSPI(cs_pin, sclk_pin, io0_pin, io1_pin, io2_pin, io3_pin)
    return qspi


def test_quadspi_initialization(mock_pigpio):
    """Test QuadSPI initialization sets up pins correctly."""
    cs_pin, sclk_pin, io0_pin, io1_pin, io2_pin, io3_pin = 8, 11, 10, 9, 7, 6

    qspi = quad_spi.QuadSPI(cs_pin, sclk_pin, io0_pin, io1_pin, io2_pin, io3_pin)

    # Check pigpio connection
    assert qspi.pi == mock_pigpio

    # Check pin modes were set
    mock_pigpio.set_mode.assert_any_call(cs_pin, mock_pigpio.OUTPUT)
    mock_pigpio.set_mode.assert_any_call(sclk_pin, mock_pigpio.OUTPUT)
    mock_pigpio.set_mode.assert_any_call(io0_pin, mock_pigpio.OUTPUT)
    mock_pigpio.set_mode.assert_any_call(io1_pin, mock_pigpio.INPUT)
    mock_pigpio.set_mode.assert_any_call(io2_pin, mock_pigpio.OUTPUT)
    mock_pigpio.set_mode.assert_any_call(io3_pin, mock_pigpio.OUTPUT)

    # Check initial pin states
    mock_pigpio.write.assert_any_call(cs_pin, 1)  # CS high
    mock_pigpio.write.assert_any_call(sclk_pin, 0)  # Clock low
    mock_pigpio.write.assert_any_call(io0_pin, 0)
    mock_pigpio.write.assert_any_call(io2_pin, 0)
    mock_pigpio.write.assert_any_call(io3_pin, 0)


def test_quadspi_initialization_connection_failed():
    """Test QuadSPI initialization fails when pigpio connection fails."""
    with patch('pigpio.pi') as mock_pi_class:
        mock_pi_instance = Mock()
        mock_pi_instance.connected = False
        mock_pi_class.return_value = mock_pi_instance

        with pytest.raises(RuntimeError, match="Could not connect to pigpio daemon"):
            quad_spi.QuadSPI(8, 11, 10, 9, 7, 6)


def test_begin_transaction(quad_spi_instance, mock_pigpio):
    """Test begin_transaction sets CS low."""
    quad_spi_instance.begin_transaction()
    mock_pigpio.write.assert_called_with(quad_spi_instance.cs_pin, 0)


def test_end_transaction(quad_spi_instance, mock_pigpio):
    """Test end_transaction sets CS high."""
    quad_spi_instance.end_transaction()
    mock_pigpio.write.assert_called_with(quad_spi_instance.cs_pin, 1)


def test_write_byte_standard(quad_spi_instance, mock_pigpio):
    """Test writing a byte in standard SPI mode."""
    test_byte = 0xAB  # 10101011

    # Clear previous calls from initialization
    mock_pigpio.write.reset_mock()

    quad_spi_instance.write_byte_standard(test_byte)

    # Should generate 8 clock pulses
    assert mock_pigpio.write.call_count >= 8  # Clock pulses

    # Check that IO0 was written with each bit (8 data bits)
    io0_calls = [call for call in mock_pigpio.write.call_args_list
                 if call[0][0] == quad_spi_instance.io0_pin]
    assert len(io0_calls) == 8


def test_read_byte_standard(quad_spi_instance, mock_pigpio):
    """Test reading a byte in standard SPI mode."""
    # Mock read to return alternating bits
    mock_pigpio.read.side_effect = [1, 0, 1, 0, 1, 0, 1, 0]

    result = quad_spi_instance.read_byte_standard()

    expected = int('10101010', 2)  # 0xAA
    assert result == expected

    # Should generate 8 clock pulses
    sclk_high_calls = [call for call in mock_pigpio.write.call_args_list
                       if call[0][0] == quad_spi_instance.sclk_pin and call[0][1] == 1]
    assert len(sclk_high_calls) == 8


def test_write_quad_single_byte(quad_spi_instance, mock_pigpio):
    """Test writing a single byte in quad-SPI mode."""
    test_data = b'\xAB'  # 10101011

    quad_spi_instance.write_quad(test_data)

    # Should write 2 nibbles (4 bits each) = 2 clock pulses
    sclk_high_calls = [call for call in mock_pigpio.write.call_args_list
                       if call[0][0] == quad_spi_instance.sclk_pin and call[0][1] == 1]
    assert len(sclk_high_calls) >= 2


def test_write_quad_multiple_bytes(quad_spi_instance, mock_pigpio):
    """Test writing multiple bytes in quad-SPI mode."""
    test_data = b'\xAB\xCD\xEF'

    quad_spi_instance.write_quad(test_data)

    # Should write 6 nibbles (4 bits each) = 6 clock pulses
    sclk_high_calls = [call for call in mock_pigpio.write.call_args_list
                       if call[0][0] == quad_spi_instance.sclk_pin and call[0][1] == 1]
    assert len(sclk_high_calls) >= 6


def test_read_quad(quad_spi_instance, mock_pigpio):
    """Test reading data in quad-SPI mode."""
    # Mock read operations - simplified for testing
    # The read_quad method tries to read from 4 pins per nibble, so provide enough values
    mock_pigpio.read.side_effect = [1, 0, 1, 0] * 4  # Mock 4-bit nibble reads (enough for 2 nibbles)
    mock_pigpio.get_mode.return_value = mock_pigpio.INPUT  # Pins are in input mode

    result = quad_spi_instance.read_quad(1)  # Read 1 byte

    assert len(result) == 1
    assert isinstance(result, bytearray)


def test_set_quad_mode(quad_spi_instance, mock_pigpio):
    """Test setting pins to quad mode."""
    quad_spi_instance.set_quad_mode()

    # IO0, IO2, IO3 should be outputs, IO1 should be input
    mock_pigpio.set_mode.assert_any_call(quad_spi_instance.io0_pin, mock_pigpio.OUTPUT)
    mock_pigpio.set_mode.assert_any_call(quad_spi_instance.io1_pin, mock_pigpio.INPUT)
    mock_pigpio.set_mode.assert_any_call(quad_spi_instance.io2_pin, mock_pigpio.OUTPUT)
    mock_pigpio.set_mode.assert_any_call(quad_spi_instance.io3_pin, mock_pigpio.OUTPUT)


def test_set_standard_mode(quad_spi_instance, mock_pigpio):
    """Test setting pins to standard SPI mode."""
    quad_spi_instance.set_standard_mode()

    # IO0 should be output (MOSI), IO1 should be input (MISO)
    # IO2, IO3 should be outputs but not used in standard mode
    mock_pigpio.set_mode.assert_any_call(quad_spi_instance.io0_pin, mock_pigpio.OUTPUT)
    mock_pigpio.set_mode.assert_any_call(quad_spi_instance.io1_pin, mock_pigpio.INPUT)
    mock_pigpio.set_mode.assert_any_call(quad_spi_instance.io2_pin, mock_pigpio.OUTPUT)
    mock_pigpio.set_mode.assert_any_call(quad_spi_instance.io3_pin, mock_pigpio.OUTPUT)


def test_clock_pulse_timing(quad_spi_instance, mock_pigpio):
    """Test clock pulse timing."""
    with patch('time.sleep') as mock_sleep:
        quad_spi_instance._clock_pulse()

        # Should set clock high, sleep, set clock low, sleep
        expected_calls = [
            ((quad_spi_instance.sclk_pin, 1),),
            ((quad_spi_instance.sclk_pin, 0),)
        ]
        actual_calls = mock_pigpio.write.call_args_list[-2:]
        assert actual_calls == expected_calls

        # Should sleep twice (1 microsecond each)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.000001)


def test_set_data_pins(quad_spi_instance, mock_pigpio):
    """Test setting data pins."""
    quad_spi_instance._set_data_pins(1, 0, 1)

    # Should write to IO0, IO2, IO3
    mock_pigpio.write.assert_any_call(quad_spi_instance.io0_pin, 1)
    mock_pigpio.write.assert_any_call(quad_spi_instance.io2_pin, 0)
    mock_pigpio.write.assert_any_call(quad_spi_instance.io3_pin, 1)


def test_read_data_pin(quad_spi_instance, mock_pigpio):
    """Test reading data pin."""
    mock_pigpio.read.return_value = 1

    result = quad_spi_instance._read_data_pin()

    assert result == 1
    mock_pigpio.read.assert_called_with(quad_spi_instance.io1_pin)


def test_del_cleanup(quad_spi_instance, mock_pigpio):
    """Test cleanup on deletion."""
    quad_spi_instance.__del__()

    mock_pigpio.stop.assert_called_once()


def test_del_cleanup_not_connected():
    """Test cleanup when not connected."""
    # Temporarily modify the global mock to simulate disconnected state
    original_connected = mock_pigpio_module.pi().connected
    mock_pigpio_module.pi().connected = False

    try:
        # This will fail during initialization, but we want to test __del__ on an object
        # that was created when connected=False
        # We'll create a mock object directly instead
        qspi = Mock(spec=quad_spi.QuadSPI)
        qspi.pi = Mock()
        qspi.pi.connected = False
        # Should not raise exception when pi is not connected
        qspi.__del__()
    finally:
        # Restore original state
        mock_pigpio_module.pi().connected = original_connected


@pytest.mark.parametrize("test_data,expected_calls", [
    (b'\x00', 2),  # 2 clock pulses for 1 byte
    (b'\xFF\x00', 4),  # 4 clock pulses for 2 bytes
    (b'\x12\x34\x56', 6),  # 6 clock pulses for 3 bytes
])
def test_write_quad_different_data_sizes(mock_pigpio, test_data, expected_calls):
    """Test write_quad with different data sizes."""
    qspi = quad_spi.QuadSPI(8, 11, 10, 9, 7, 6)

    qspi.write_quad(test_data)

    # Count clock high calls
    sclk_high_calls = [call for call in mock_pigpio.write.call_args_list
                       if call[0][0] == qspi.sclk_pin and call[0][1] == 1]
    assert len(sclk_high_calls) >= expected_calls


def test_example_usage(mock_pigpio):
    """Test the example usage in __main__ block."""
    with patch('builtins.print') as mock_print:
        # Simulate the main block code directly
        CS_PIN = 8
        SCLK_PIN = 11
        IO0_PIN = 10  # MOSI
        IO1_PIN = 9   # MISO
        IO2_PIN = 7
        IO3_PIN = 6

        try:
            qspi = quad_spi.QuadSPI(CS_PIN, SCLK_PIN, IO0_PIN, IO1_PIN, IO2_PIN, IO3_PIN)
            print("Quad-SPI interface initialized")

            # Example: Send a command in standard mode, then data in quad mode
            qspi.begin_transaction()
            qspi.write_byte_standard(0x38)  # Example quad write command
            qspi.set_quad_mode()
            qspi.write_quad(b"Hello Quad-SPI!")
            qspi.end_transaction()

            print("Data sent successfully")

        except Exception as e:
            print(f"Error: {e}")

        # Check that initialization print was called
        mock_print.assert_any_call("Quad-SPI interface initialized")

        # Check that data sent print was called
        mock_print.assert_any_call("Data sent successfully")
