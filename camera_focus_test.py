#!/usr/bin/env python3
"""
카메라 초점 맞추기를 위한 실시간 영상 테스트 유틸리티

사용법:
    python camera_focus_test.py --camera-ids 0 1 2 3  # 특정 카메라들만
    python camera_focus_test.py  # 모든 카메라
    
키보드 단축키:
    - 'q' 또는 ESC: 종료
    - 's': 현재 프레임을 이미지로 저장
    - 'f': FPS 정보 토글
"""

import argparse
import time
from pathlib import Path
import cv2
import numpy as np
from datetime import datetime

from lerobot.common.robot_devices.cameras.opencv import find_cameras, OpenCVCamera
from lerobot.common.robot_devices.cameras.configs import OpenCVCameraConfig


def create_focus_overlay(image, camera_idx):
    """이미지에 초점 확인을 위한 오버레이 추가"""
    h, w = image.shape[:2]
    overlay = image.copy()
    
    # 중앙에 십자선 그리기
    center_x, center_y = w // 2, h // 2
    cv2.line(overlay, (center_x - 50, center_y), (center_x + 50, center_y), (0, 255, 0), 2)
    cv2.line(overlay, (center_x, center_y - 50), (center_x, center_y + 50), (0, 255, 0), 2)
    
    # 카메라 정보 텍스트
    cv2.putText(overlay, f'Camera {camera_idx}', (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # 해상도 정보
    cv2.putText(overlay, f'{w}x{h}', (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 초점 확인을 위한 격자 (옵션)
    grid_spacing = 100
    for x in range(0, w, grid_spacing):
        cv2.line(overlay, (x, 0), (x, h), (128, 128, 128), 1)
    for y in range(0, h, grid_spacing):
        cv2.line(overlay, (0, y), (w, y), (128, 128, 128), 1)
    
    return overlay


def calculate_sharpness(image):
    """이미지의 선명도 계산 (라플라시안 분산 사용)"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return laplacian.var()


def main():
    parser = argparse.ArgumentParser(description="카메라 초점 맞추기 테스트 유틸리티")
    parser.add_argument(
        "--camera-ids",
        type=int,
        nargs="*",
        default=None,
        help="테스트할 카메라 인덱스들. 미지정시 모든 카메라 사용",
    )
    parser.add_argument(
        "--save-dir",
        type=Path,
        default="outputs/focus_test_captures",
        help="스냅샷 저장 디렉토리",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=None,
        help="카메라 FPS 설정",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="카메라 가로 해상도",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="카메라 세로 해상도",
    )
    
    args = parser.parse_args()
    
    # 사용 가능한 카메라 찾기
    if args.camera_ids is None or len(args.camera_ids) == 0:
        camera_infos = find_cameras()
        camera_ids = [cam["index"] for cam in camera_infos]
    else:
        camera_ids = args.camera_ids
    
    if not camera_ids:
        print("사용 가능한 카메라가 없습니다!")
        return
    
    print(f"테스트할 카메라들: {camera_ids}")
    print("\n키보드 단축키:")
    print("  'q' 또는 ESC: 종료")
    print("  's': 현재 프레임을 이미지로 저장")
    print("  'f': FPS 정보 토글")
    print("  'g': 격자 오버레이 토글")
    print("\n각 카메라 창을 클릭해서 활성화한 후 키를 누르세요.\n")
    
    # 카메라 초기화
    cameras = []
    for cam_idx in camera_ids:
        try:
            config = OpenCVCameraConfig(
                camera_index=cam_idx, 
                fps=args.fps, 
                width=args.width, 
                height=args.height
            )
            camera = OpenCVCamera(config)
            camera.connect()
            print(f"카메라 {cam_idx} 연결 완료: {camera.capture_width}x{camera.capture_height} @ {camera.fps}fps")
            cameras.append(camera)
        except Exception as e:
            print(f"카메라 {cam_idx} 연결 실패: {e}")
    
    if not cameras:
        print("연결된 카메라가 없습니다!")
        return
    
    # 저장 디렉토리 생성
    args.save_dir.mkdir(parents=True, exist_ok=True)
    
    # 실시간 영상 표시
    show_fps = False
    show_grid = True
    fps_times = []
    
    try:
        while True:
            start_time = time.time()
            
            for camera in cameras:
                try:
                    # 이미지 읽기
                    image = camera.read()
                    
                    # BGR로 변환 (OpenCV 디스플레이용)
                    if camera.color_mode == "rgb":
                        display_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    else:
                        display_image = image.copy()
                    
                    # 오버레이 추가
                    if show_grid:
                        display_image = create_focus_overlay(display_image, camera.camera_index)
                    
                    # 선명도 정보 추가
                    sharpness = calculate_sharpness(display_image)
                    cv2.putText(display_image, f'Sharpness: {sharpness:.1f}', (10, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    
                    # FPS 정보 추가
                    if show_fps and fps_times:
                        current_fps = len(fps_times)
                        cv2.putText(display_image, f'FPS: {current_fps:.1f}', (10, 120), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    
                    # 윈도우에 표시
                    window_name = f'Camera {camera.camera_index} - Focus Test'
                    cv2.imshow(window_name, display_image)
                    
                except Exception as e:
                    print(f"카메라 {camera.camera_index} 읽기 오류: {e}")
            
            # FPS 계산을 위한 시간 관리
            current_time = time.time()
            fps_times.append(current_time)
            fps_times = [t for t in fps_times if current_time - t < 1.0]  # 1초 내 프레임만 유지
            
            # 키보드 입력 처리
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:  # 'q' 또는 ESC
                break
            elif key == ord('s'):  # 스냅샷 저장
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                for camera in cameras:
                    try:
                        image = camera.read()
                        filename = args.save_dir / f"camera_{camera.camera_index:02d}_{timestamp}.png"
                        
                        # PIL Image로 변환해서 저장
                        from PIL import Image
                        if camera.color_mode == "rgb":
                            pil_image = Image.fromarray(image)
                        else:
                            # BGR to RGB 변환
                            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                            pil_image = Image.fromarray(rgb_image)
                        
                        pil_image.save(str(filename), quality=100)
                        print(f"저장됨: {filename}")
                    except Exception as e:
                        print(f"카메라 {camera.camera_index} 저장 오류: {e}")
            elif key == ord('f'):  # FPS 토글
                show_fps = not show_fps
                print(f"FPS 표시: {'ON' if show_fps else 'OFF'}")
            elif key == ord('g'):  # 격자 토글
                show_grid = not show_grid
                print(f"격자 표시: {'ON' if show_grid else 'OFF'}")
    
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
    
    finally:
        # 정리
        for camera in cameras:
            try:
                camera.disconnect()
            except:
                pass
        cv2.destroyAllWindows()
        print("카메라 연결 해제 완료")


if __name__ == "__main__":
    main() 