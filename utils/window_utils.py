# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'

import numpy as np
import pyautogui
import win32con
import win32gui
import win32ui
from ctypes import windll

# 尝试导入 dxcam（DX11/DX12 截图支持）
try:
    import dxcam
    DXCAM_AVAILABLE = True
except ImportError:
    DXCAM_AVAILABLE = False

# PrintWindow 标志
PW_CLIENTONLY = 1
PW_RENDERFULLCONTENT = 2  # Windows 8.1+ 支持捕获 DX 内容


def get_window_handle(window_title):
    """
    获取窗口句柄
    :param window_title:
    :return:
    """
    handle = win32gui.FindWindow(None, window_title)
    if handle == 0:
        raise Exception(f"根据窗口标题'{window_title}' 没有找到窗口.")
    return handle


def get_window_rect(handle):
    """
    获取窗口位置和大小
    :param handle:
    :return:
    """
    rect = win32gui.GetWindowRect(handle)
    x1, y1, x2, y2 = rect
    width = x2 - x1
    height = y2 - y1
    return x1, y1, width, height


def capture_window_image(handle):
    """
    截取窗口图像
    :param handle:
    :return:
    """
    x, y, width, height = get_window_rect(handle)
    screenshot = pyautogui.screenshot(region=(x, y, width, height))
    return screenshot


def capture_window_BGRX(hwnd, region=None):
    """
    BGRX
    region(offset_x, offset_y, width, height)
    """

    # 获取窗口大小
    left, top, right, bot = win32gui.GetClientRect(hwnd)
    w = right - left
    h = bot - top

    if region:
        offset_x, offset_y, width, height = region
        left = left + offset_x
        top = top + offset_y
        w = width
        h = height

    # 获取窗口的设备上下文DC（Device Context）
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    # 创建位图对象
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    # 复制窗口内容到位图
    saveDC.BitBlt((0, 0), (w, h), mfcDC, (left, top), win32con.SRCCOPY)

    # 将位图转换为PIL Image对象
    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)

    img = np.frombuffer(bmpstr, dtype='uint8')
    img = img.reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))

    # 清理资源
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    return img


def crop_image(image, x, y, width, height):
    """
    从图像中截取指定区域
    :param image: 原始图像 (numpy array)
    :param x: 左上角的x坐标
    :param y: 左上角的y坐标
    :param width: 截取区域的宽度
    :param height: 截取区域的高度
    :return: 截取后的图像
    """
    return image[y:y + height, x:x + width]


class WindowCapture:
    """
    窗口截图类，支持 DX11 游戏截图
    
    截图模式优先级:
    1. dxcam - 最佳DX11/DX12支持，需要安装dxcam库
    2. PrintWindow - Windows原生，支持DX窗口化
    3. BitBlt - 传统GDI截图，不支持DX硬件加速
    
    支持上下文管理器协议
    """
    def __init__(self, hwnd, use_printwindow=False, use_dxcam=True):
        """
        初始化窗口截图
        
        Args:
            hwnd: 窗口句柄
            use_printwindow: 是否使用PrintWindow，默认False
            use_dxcam: 是否使用dxcam（DX11支持），默认True
        """
        self.hwnd = hwnd
        self.use_printwindow = use_printwindow
        self.use_dxcam = use_dxcam and DXCAM_AVAILABLE
        self._released = False
        self._dxcam_camera = None
        self._init_resources()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

    def _init_resources(self):
        # 获取窗口位置和客户区尺寸
        left, top, right, bot = win32gui.GetClientRect(self.hwnd)
        self.width = right - left
        self.height = bot - top
        
        # 获取窗口在屏幕上的位置（用于dxcam区域截图）
        rect = win32gui.GetWindowRect(self.hwnd)
        self.window_left = rect[0]
        self.window_top = rect[1]
        
        # 计算客户区在屏幕上的位置
        import ctypes
        point = ctypes.wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(self.hwnd, ctypes.byref(point))
        self.client_left = point.x
        self.client_top = point.y

        # 初始化 dxcam（如果可用）
        if self.use_dxcam:
            try:
                self._dxcam_camera = dxcam.create(output_color="BGR")
                print(f"[WindowCapture] 使用 dxcam 模式 (DX11/DX12支持)")
            except Exception as e:
                print(f"[WindowCapture] dxcam 初始化失败: {e}，回退到传统模式")
                self.use_dxcam = False
                self._dxcam_camera = None

        # 创建设备上下文（传统模式备用）
        self.wdc = win32gui.GetWindowDC(self.hwnd)
        self.dc = win32ui.CreateDCFromHandle(self.wdc)
        self.mem_dc = self.dc.CreateCompatibleDC()

        # 创建位图对象
        self.bitmap = win32ui.CreateBitmap()
        self.bitmap.CreateCompatibleBitmap(self.dc, self.width, self.height)
        self.mem_dc.SelectObject(self.bitmap)

        # 预分配numpy数组内存
        self.buffer = np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def capture(self):
        if self.use_dxcam and self._dxcam_camera:
            return self._capture_dxcam()
        elif self.use_printwindow:
            return self._capture_printwindow()
        else:
            return self._capture_bitblt()
    
    def _capture_dxcam(self):
        """使用 dxcam 截图，支持 DX11/DX12"""
        try:
            # 计算截图区域（客户区在屏幕上的位置）
            region = (
                self.client_left,
                self.client_top,
                self.client_left + self.width,
                self.client_top + self.height
            )
            frame = self._dxcam_camera.grab(region=region)
            if frame is not None:
                np.copyto(self.buffer, frame)
                return self.buffer
            else:
                # dxcam 返回 None，回退到其他方式
                return self._capture_printwindow()
        except Exception as e:
            print(f"[WindowCapture] dxcam 截图失败: {e}")
            return self._capture_printwindow()

    def _capture_printwindow(self):
        """使用 PrintWindow 截图，支持 DX11 窗口化模式"""
        # PW_CLIENTONLY (1) 只截取客户区，不包含标题栏和边框
        # PW_RENDERFULLCONTENT (2) 可以捕获 DX 渲染内容 (Win8.1+)
        # 组合使用: PW_CLIENTONLY | PW_RENDERFULLCONTENT = 3
        result = windll.user32.PrintWindow(
            self.hwnd, 
            self.mem_dc.GetSafeHdc(), 
            PW_CLIENTONLY | PW_RENDERFULLCONTENT
        )
        
        if result == 0:
            # PrintWindow 失败，尝试只用 PW_CLIENTONLY
            result = windll.user32.PrintWindow(
                self.hwnd, 
                self.mem_dc.GetSafeHdc(), 
                PW_CLIENTONLY
            )
        
        if result == 0:
            # 都失败了，回退到 BitBlt
            return self._capture_bitblt()

        # 获取位图数据
        bits = self.bitmap.GetBitmapBits(True)
        img = np.frombuffer(bits, dtype=np.uint8).reshape(
            (self.height, self.width, 4))[..., :3]
        np.copyto(self.buffer, img)
        return self.buffer

    def _capture_bitblt(self):
        """传统 BitBlt 截图"""
        self.mem_dc.BitBlt((0, 0), (self.width, self.height),
                           self.dc, (0, 0), win32con.SRCCOPY)

        bits = self.bitmap.GetBitmapBits(True)
        img = np.frombuffer(bits, dtype=np.uint8).reshape(
            (self.height, self.width, 4))[..., :3]
        np.copyto(self.buffer, img)
        return self.buffer

    def release(self):
        """释放资源，可重复调用"""
        if self._released:
            return
        try:
            # 释放 dxcam
            if self._dxcam_camera:
                try:
                    del self._dxcam_camera
                except:
                    pass
                self._dxcam_camera = None
            
            # 释放 GDI 资源
            win32gui.DeleteObject(self.bitmap.GetHandle())
            self.mem_dc.DeleteDC()
            self.dc.DeleteDC()
            win32gui.ReleaseDC(self.hwnd, self.wdc)
        finally:
            self._released = True

    def __del__(self):
        """析构时确保资源释放"""
        self.release()
