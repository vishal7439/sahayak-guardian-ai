
#!/usr/bin/env python3

"""Sahayak ROS 2 detection publisher.

Reuses the existing BPU YOLO (sahayak_vision) and publishes detections

on the /sahayak/detections topic. Demonstrates real ROS 2 node communication

alongside the main Flask system."""

import sys, json, time

import rclpy

from rclpy.node import Node

from std_msgs.msg import String



# reuse the existing BPU vision module

VDIR = "/app/pydev_demo/02_detection_sample/03_ultralytics_yolov8"

if VDIR not in sys.path:

    sys.path.insert(0, VDIR)



class DetectionPublisher(Node):

    def __init__(self):

        super().__init__('sahayak_detection_publisher')

        self.pub = self.create_publisher(String, '/sahayak/detections', 10)

        self.timer = self.create_timer(1.0, self.tick)   # 1 Hz

        try:

            import sahayak_vision

            self.vision = sahayak_vision

            self.get_logger().info('BPU vision loaded — publishing real YOLO detections')

        except Exception as e:

            self.vision = None

            self.get_logger().warn(f'vision not available ({e}) — publishing empty')



    def tick(self):

        objects = []

        if self.vision is not None:

            try:

                dets = self.vision.detect()   # [(name, score), ...]

                objects = [{"name": n, "score": round(float(s), 2)} for n, s in dets if s >= 0.4]

            except Exception as e:

                self.get_logger().error(f'detect failed: {e}')

        msg = String()

        msg.data = json.dumps({"stamp": time.time(), "objects": objects})

        self.pub.publish(msg)

        self.get_logger().info(f'published {len(objects)} objects on /sahayak/detections')



def main():

    rclpy.init()

    node = DetectionPublisher()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()



if __name__ == '__main__':

    main()

