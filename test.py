import serial
import time
import struct

class MotorDriver:
    def __init__(self):
        # 시리얼 포트 설정 (필요 시 수정)
        self.ser = serial.Serial('/dev/motor', baudrate=19200, timeout=1)

    def send_rpm(self, rpm_left, rpm_right):
        # 리틀엔디언 방식으로 RPM 값을 2바이트로 변환 (부호 있는 값)
        rpm1_bytes = struct.pack('<h', rpm_left)  # <h: 리틀엔디언 2바이트 정수 (short)
        rpm2_bytes = struct.pack('<h', rpm_right)  # <h: 리틀엔디언 2바이트 정수 (short)

        # 패킷 구성 (모터 제어용 패킷)
        packet = [183, 184, 1, 207, 7, 1]
        packet.extend(rpm1_bytes)  # 모터1 RPM (리틀엔디언)
        packet.append(1)  # 임시 값 (적절한 값으로 대체 가능)
        packet.extend(rpm2_bytes)  # 모터2 RPM (리틀엔디언)
        packet.append(0)  # 임시 값 (적절한 값으로 대체 가능)

        # 체크섬 계산 및 추가
        checksum = self.calculate_checksum(packet)
        packet.append(checksum)

        # 시리얼 전송
        self.send_packet(packet)

    def send_packet(self, packet):
        # 패킷 전송
        self.ser.write(bytearray(packet))
        print(f"[TX] Sent packet: {[hex(b) for b in packet]}")

    def read_response(self):
        # 응답을 위한 패킷 전송 (모터 상태 확인)
        packet_to_send = [183, 184, 1, 4, 1, 216]
        checksum = self.calculate_checksum(packet_to_send)
        packet_to_send.append(checksum)

        # 패킷 전송
        self.send_packet(packet_to_send)

        # 1초 대기 후 응답 읽기
        print("Waiting for response... (1 second)")
        time.sleep(1)

        if self.ser.in_waiting > 0:
            data = self.ser.read(self.ser.in_waiting)
            print(f"[RX] Received: {[hex(b) for b in data]}")
            self.parse_response(data)  # 응답 파싱 함수 호출
        else:
            print("[RX] No data")

    def parse_response(self, data):
        """
        응답 데이터를 파싱하는 함수
        """
        try:
            # 패킷 길이에 따라 처리 (14바이트 또는 16바이트)
            packet_length = data[4]  # 패킷 길이 (14 또는 16)
            if packet_length == 14:
                self.parse_14byte_response(data)
            elif packet_length == 16:
                self.parse_16byte_response(data)
            else:
                print(f"Unexpected packet length: {packet_length}")
        except Exception as e:
            print(f"Error parsing response: {e}")

    def parse_14byte_response(self, data):
        """
        14바이트 응답 패킷을 파싱하는 함수
        """
        # 앞 5개 항목을 제외하고 데이터를 읽기 (패킷은 [0, 1, 2, 3, 4]를 제외)
        data = data[5:-1]  # 마지막 체크섬은 제외하고 데이터를 읽는다.
        
        # 리틀 엔디언으로 RPM 값 추출 (2바이트)
        rpm_motor1 = struct.unpack('<h', bytes(data[0:2]))[0]  # <h: 리틀엔디언 2바이트 정수
        rpm_motor2 = struct.unpack('<h', bytes(data[7:9]))[0]  # <h: 리틀엔디언 2바이트 정수

        # 상태 변수 (각각 1바이트)
        status_motor1 = data[2]
        status_motor2 = data[9]

        # 위치 추출 (4바이트, 리틀엔디언)
        position_motor1 = struct.unpack('<i', bytes(data[3:7]))[0]  # <i: 리틀엔디언 4바이트 정수
        position_motor2 = struct.unpack('<i', bytes(data[10:14]))[0]  # <i: 리틀엔디언 4바이트 정수

        # 휠 회전수 계산 (기어비 1/100, 엔코더 한 바퀴 6535)
        wheel_rotations_motor1 = (position_motor1 / 6535)/100  # 수정된 회전수 계산
        wheel_rotations_motor2 = (position_motor2 / 6535)/100  # 수정된 회전수 계산

        # 결과 출력
        print(f"Motor 1 RPM: {rpm_motor1}, Motor 1 Status: {status_motor1}, Motor 1 Position: {position_motor1}, Wheel 1 Rotations: {wheel_rotations_motor1}")
        print(f"Motor 2 RPM: {rpm_motor2}, Motor 2 Status: {status_motor2}, Motor 2 Position: {position_motor2}, Wheel 2 Rotations: {wheel_rotations_motor2}")

    def parse_16byte_response(self, data):
        """
        16바이트 응답 패킷을 파싱하는 함수
        """
        # 앞 5개 항목을 제외하고 데이터를 읽기 (패킷은 [0, 1, 2, 3, 4]를 제외)
        data = data[5:-1]  # 마지막 체크섬은 제외하고 데이터를 읽는다.

        # 리틀 엔디언으로 RPM 값 추출 (2바이트)
        rpm_motor1 = struct.unpack('<h', bytes(data[0:2]))[0]  # <h: 리틀엔디언 2바이트 정수
        rpm_motor2 = struct.unpack('<h', bytes(data[7:9]))[0]  # <h: 리틀엔디언 2바이트 정수

        # 상태 변수 (각각 1바이트)
        status_motor1 = data[2]
        status_motor2 = data[9]

        # 위치 추출 (4바이트, 리틀엔디언)
        position_motor1 = struct.unpack('<i', bytes(data[3:7]))[0]  # <i: 리틀엔디언 4바이트 정수
        position_motor2 = struct.unpack('<i', bytes(data[10:14]))[0]  # <i: 리틀엔디언 4바이트 정수

        # 휠 회전수 계산 (기어비 1/100, 엔코더 한 바퀴 6535)
        wheel_rotations_motor1 = position_motor1 / 6535  # 수정된 회전수 계산
        wheel_rotations_motor2 = position_motor2 / 6535  # 수정된 회전수 계산

        # 모터 1 IO 상태 (2바이트, 리틀엔디언)
        motor1_io = struct.unpack('<h', bytes(data[14:16]))[0]
        motor2_io = struct.unpack('<h', bytes(data[16:18]))[0]

        # IO 비트 해석
        int_speed = motor1_io & 0x01
        alarm_reset = (motor1_io >> 1) & 0x01
        dir_motor1 = (motor1_io >> 2) & 0x01
        run_brake_motor1 = (motor1_io >> 3) & 0x01
        start_stop_motor1 = (motor1_io >> 4) & 0x01
        enc_b_motor1 = (motor1_io >> 5) & 0x01
        enc_a_motor1 = (motor1_io >> 6) & 0x01
        
        # 결과 출력
        print(f"Motor 1 RPM: {rpm_motor1}, Motor 1 Status: {status_motor1}, Motor 1 Position: {position_motor1}, Wheel 1 Rotations: {wheel_rotations_motor1}")
        print(f"Motor 2 RPM: {rpm_motor2}, Motor 2 Status: {status_motor2}, Motor 2 Position: {position_motor2}, Wheel 2 Rotations: {wheel_rotations_motor2}")
        print(f"Motor 1 IO: {motor1_io}, Motor 2 IO: {motor2_io}")
        print(f"Motor 1 IO Status -> INT_SPEED: {int_speed}, ALARM_RESET: {alarm_reset}, DIR: {dir_motor1}, RUN/BRAKE: {run_brake_motor1}, START/STOP: {start_stop_motor1}, ENC_B: {enc_b_motor1}, ENC_A: {enc_a_motor1}")

    def calculate_checksum(self, packet):
        checksum_value = sum(packet) & 0xFF
        checksum = (~checksum_value + 1) & 0xFF
        return checksum

    def close(self):
        self.ser.close()

def main():
    driver = MotorDriver()

    # 엔코더 초기화 패킷 전송
    init_packet = [183, 184, 1, 10, 1, 10]
    init_checksum = driver.calculate_checksum(init_packet)
    init_packet.append(init_checksum)
    driver.send_packet(init_packet)
    print("[TX] Sent Encoder initialization packet")

    # RPM 입력 받기
    rpm_left = int(input("Enter LEFT wheel RPM: "))
    rpm_right = int(input("Enter RIGHT wheel RPM: "))
    driver.send_rpm(rpm_left, rpm_right)

    try:
        while True:
            # 1초마다 엔코더 값 읽기
            time.sleep(1)
            driver.read_response()

    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        driver.close()

if __name__ == "__main__":
    main()
