#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
from geometry_msgs.msg import PoseStamped

class PoseTimestampRepublisher:
    def __init__(self):
        # 发布者：发布新的 PoseStamped 带当前时间戳
        self.pub = rospy.Publisher("/pose/with_timestamp", PoseStamped, queue_size=10)

        # 订阅者：监听原始 MAVROS 的位姿消息
        self.sub = rospy.Subscriber("/mavros/local_position/pose", PoseStamped, self.callback)

        rospy.loginfo("节点已启动，正在监听 /mavros/local_position/pose")

    def callback(self, msg):
        # 复制消息，并替换时间戳为当前时间
        new_msg = PoseStamped()
        new_msg.header.stamp = rospy.Time.now()
        new_msg.header.frame_id = msg.header.frame_id  # 可保留原始frame_id，或自行指定
        new_msg.pose = msg.pose  # 保留位姿内容

        # 发布新消息
        self.pub.publish(new_msg)
        rospy.loginfo("已发布带新时间戳的 Pose")

if __name__ == '__main__':
    rospy.init_node('pose_timestamp_republisher')
    republisher = PoseTimestampRepublisher()
    rospy.spin()

