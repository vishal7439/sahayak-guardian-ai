
#!/usr/bin/env python3

"""Sahayak ROS 2 detection subscriber.

Subscribes to /sahayak/detections and logs received messages.

Demonstrates real ROS 2 node-to-node communication for the Sahayak system."""

import json

import rclpy

from rclpy.node import Node

from std_msgs.msg import String



class DetectionSubscriber(Node):

    def __init__(self):

        super().__init__('sahayak_detection_subscriber')

        self.sub = self.create_subscription(

            String, '/sahayak/detections', self.on_msg, 10)

        self.get_logger().info('listening on /sahayak/detections')



    def on_msg(self, msg):

        try:

            data = json.loads(msg.data)

            objs = data.get("objects", [])

            if objs:

                names = ", ".join(f'{o["name"]}({o["score"]})' for o in objs)

                self.get_logger().info(f'received {len(objs)} objects: {names}')

            else:

                self.get_logger().info('received frame: no objects')

        except Exception as e:

            self.get_logger().error(f'parse failed: {e}')



def main():

    rclpy.init()

    node = DetectionSubscriber()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()



if __name__ == '__main__':

    main()

