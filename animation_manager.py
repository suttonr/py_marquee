"""
Animation Manager - Handles all marquee animations in a dedicated thread
"""
import time
import threading
import sys

class AnimationManager:
    def __init__(self, frame_rate=0.1):
        self.animation_callbacks = []  # List of {'callback': func, 'last_called': timestamp, 'interval': seconds}
        self.running = False
        self.thread = None
        self.frame_rate = frame_rate
        self.lock = threading.Lock()

    def register_animation(self, callback, interval):
        """Register a callback to be called every 'interval' seconds"""
        with self.lock:
            self.animation_callbacks.append({
                'callback': callback,
                'last_called': 0,
                'interval': interval
            })
        print(f"Registered animation callback with interval {interval}, total: {len(self.animation_callbacks)}")

    def unregister_animation(self, callback):
        """Remove a callback from the animation registry"""
        with self.lock:
            self.animation_callbacks[:] = [a for a in self.animation_callbacks if a['callback'] != callback]
        print(f"Unregistered animation callback, remaining: {len(self.animation_callbacks)}")

    def start(self):
        """Start the animation processing thread"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._animation_loop, name="AnimationThread")
        self.thread.daemon = True
        self.thread.start()
        print("Animation manager started")

    def stop(self):
        """Stop the animation processing thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("Animation manager stopped")

    def _animation_loop(self):
        """Main animation processing loop"""
        while self.running:
            current_time = time.time()

            # Process all registered animations
            with self.lock:
                callbacks_to_process = self.animation_callbacks[:]

            for animation in callbacks_to_process:
                try:
                    if current_time - animation['last_called'] >= animation['interval']:
                        animation['callback'](current_time)
                        animation['last_called'] = current_time
                except Exception as e:
                    print(f"Animation callback error: {e}")
                    # Remove broken callbacks
                    try:
                        with self.lock:
                            if animation in self.animation_callbacks:
                                self.animation_callbacks.remove(animation)
                    except ValueError:
                        pass  # Already removed

            time.sleep(self.frame_rate) 

# Global animation manager instance
_animation_manager = None

def get_animation_manager():
    """Get the global animation manager instance"""
    global _animation_manager
    if _animation_manager is None:
        _animation_manager = AnimationManager()
    return _animation_manager

def register_animation(callback, interval):
    """Global function to register animations"""
    get_animation_manager().register_animation(callback, interval)

def unregister_animation(callback):
    """Global function to unregister animations"""
    get_animation_manager().unregister_animation(callback)

def start_animation_manager():
    """Start the global animation manager"""
    get_animation_manager().start()

def stop_animation_manager():
    """Stop the global animation manager"""
    if _animation_manager:
        _animation_manager.stop()
