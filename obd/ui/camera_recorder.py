import numpy as np
import threading
import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QImage, QPixmap
import sounddevice as sd
from scipy.io import wavfile
import tempfile
import os


class RecorderSignals(QObject):
    """Signals for thread-safe communication"""
    frame_ready = pyqtSignal(np.ndarray)
    status_changed = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    recording_complete = pyqtSignal()
    playback_complete = pyqtSignal()


class CameraRecorder(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera & Audio Recorder")
        self.resize(640, 720)
        self.setStyleSheet(
            "QWidget { background: #020202; color: #7CFC00; }"
            "QLabel { color: #78ff78; font-weight: bold; }"
        )
        
        self.signals = RecorderSignals()
        self.signals.frame_ready.connect(self._on_frame_ready)
        self.signals.status_changed.connect(self._on_status_changed)
        self.signals.progress_updated.connect(self._on_progress_updated)
        self.signals.recording_complete.connect(self._on_recording_complete)
        self.signals.playback_complete.connect(self._on_playback_complete)
        
        self.cap = None
        self.frames = []
        self.audio_data = None
        self.recording = False
        self.playback = False
        self.frame_rate = 30
        self.width = 640
        self.height = 480
        self.audio_samplerate = 44100
        self.current_frame = None
        
        self._build_ui()
        self._start_recording()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Title
        title = QLabel("CAMERA & AUDIO RECORDING")
        title.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #9cff9c;")
        layout.addWidget(title)
        
        # Camera feed label
        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setStyleSheet("border: 2px solid #0f0; background: #000;")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.camera_label)
        
        # Status label
        self.status_label = QLabel("Initializing camera and audio...")
        self.status_label.setFont(QFont("Consolas", 10))
        self.status_label.setStyleSheet("color: #7cff7c;")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setStyleSheet(
            "QProgressBar { border: 1px solid #0f0; background: #010101; }"
            "QProgressBar::chunk { background: #1fbf1f; }"
        )
        layout.addWidget(self.progress)
        
        # Close button
        self.close_button = QPushButton("Close Window")
        self.close_button.setStyleSheet(
            "QPushButton {"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0b470b, stop:1 #1fbf1f);"
            "  color: #020202;"
            "  border: 1px solid #20d020;"
            "  border-radius: 8px;"
            "  padding: 10px 12px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2bff2b, stop:1 #18b918); }"
            "QPushButton:pressed { background: #0f7f0f; }"
        )
        self.close_button.clicked.connect(self.close)
        self.close_button.setEnabled(False)
        layout.addWidget(self.close_button)
        
        # Timer for frame updates
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self._update_frame)
        self.frame_timer.start(33)  # ~30 fps
    
    def _start_recording(self):
        """Start camera and audio capture"""
        threading.Thread(target=self._record_thread, daemon=True).start()
    
    def _record_thread(self):
        """Thread to handle camera and audio recording"""
        try:
            # Open camera
            import cv2
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.signals.status_changed.emit("ERROR: Camera not accessible")
                return
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.frame_rate)
            
            self.recording = True
            self.signals.status_changed.emit("Recording... 10 seconds (video & audio)")
            
            record_start = time.time()
            record_duration = 10.0
            
            # Audio recording parameters
            audio_duration = int(record_duration * self.audio_samplerate)
            audio_buffer = np.zeros(audio_duration, dtype=np.float32)
            audio_index = 0
            
            # Start audio capture
            def audio_callback(indata, frames, time_info, status):
                nonlocal audio_index
                if status:
                    print(f"Audio status: {status}")
                chunk = indata[:, 0].astype(np.float32)
                frames_to_copy = min(len(chunk), len(audio_buffer) - audio_index)
                audio_buffer[audio_index:audio_index + frames_to_copy] = chunk[:frames_to_copy]
                audio_index += frames_to_copy
            
            # Start audio stream
            audio_stream = sd.InputStream(
                samplerate=self.audio_samplerate,
                channels=1,
                callback=audio_callback,
                blocksize=2048
            )
            audio_stream.start()
            
            # Record frames for 10 seconds
            while time.time() - record_start < record_duration and self.recording:
                ret, frame = self.cap.read()
                if ret:
                    self.frames.append(frame.copy())
                    elapsed = time.time() - record_start
                    progress_val = int((elapsed / record_duration) * 100)
                    self.signals.progress_updated.emit(min(progress_val, 100))
                time.sleep(0.01)
            
            audio_stream.stop()
            audio_stream.close()
            
            # Trim audio buffer to actual recorded samples
            self.audio_data = audio_buffer[:audio_index]
            
            self.recording = False
            self.signals.status_changed.emit(
                f"Recording complete. {len(self.frames)} frames and {audio_index} audio samples captured. Waiting 2 seconds..."
            )
            self.signals.progress_updated.emit(100)
            self.signals.recording_complete.emit()
            
            # 2 second gap
            time.sleep(2)
            
            # Playback
            self._playback_recording()
            
        except Exception as error:
            self.signals.status_changed.emit(f"Error: {error}")
            import traceback
            traceback.print_exc()
    
    def _update_frame(self):
        """Update displayed frame from camera or playback"""
        if self.current_frame is not None:
            self._display_frame(self.current_frame)
            self.current_frame = None
        elif self.cap and not self.playback:
            ret, frame = self.cap.read()
            if ret:
                self.signals.frame_ready.emit(frame)
    
    def _on_frame_ready(self, frame):
        """Handle frame from recording thread"""
        self.current_frame = frame
    
    def _on_status_changed(self, status):
        """Update status label"""
        self.status_label.setText(status)
    
    def _on_progress_updated(self, value):
        """Update progress bar"""
        self.progress.setValue(value)
    
    def _on_recording_complete(self):
        """Handle recording completion"""
        pass
    
    def _display_frame(self, frame):
        """Convert and display frame in UI"""
        try:
            import cv2
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            scaled = pixmap.scaledToWidth(640, Qt.TransformationMode.SmoothTransformation)
            self.camera_label.setPixmap(scaled)
        except Exception as error:
            print(f"Display error: {error}")
    
    def _playback_recording(self):
        """Playback recorded frames and audio"""
        if not self.frames:
            self.signals.status_changed.emit("No frames recorded")
            return
        
        try:
            self.playback = True
            self.signals.status_changed.emit(f"Replaying recording... ({len(self.frames)} frames)")
            self.signals.progress_updated.emit(0)
            
            frame_delay = 1.0 / self.frame_rate
            playback_start = time.time()
            playback_duration = len(self.frames) * frame_delay
            
            # Play audio in a separate thread to avoid blocking
            if self.audio_data is not None and len(self.audio_data) > 0:
                audio_thread = threading.Thread(
                    target=lambda: sd.play(self.audio_data, self.audio_samplerate),
                    daemon=True
                )
                audio_thread.start()
            
            # Play video frames
            for idx, frame in enumerate(self.frames):
                if not self.playback:
                    break
                
                self.signals.frame_ready.emit(frame)
                elapsed = time.time() - playback_start
                progress_val = int((elapsed / playback_duration) * 100)
                self.signals.progress_updated.emit(min(progress_val, 100))
                
                time.sleep(frame_delay)
            
            self.playback = False
            self.signals.status_changed.emit("Playback complete. You can close the window.")
            self.signals.progress_updated.emit(100)
            self.signals.playback_complete.emit()
            self.close_button.setEnabled(True)
            
        except Exception as error:
            self.signals.status_changed.emit(f"Playback error: {error}")
            import traceback
            traceback.print_exc()
    
    def _on_playback_complete(self):
        """Handle playback completion"""
        pass
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        self.recording = False
        self.playback = False
        if self.cap:
            self.cap.release()
        if self.frame_timer:
            self.frame_timer.stop()
        event.accept()

