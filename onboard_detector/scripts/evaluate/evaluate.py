#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import numpy as np
from geometry_msgs.msg import PoseStamped, TwistStamped
from visualization_msgs.msg import MarkerArray
from geometry_msgs.msg import Point

class BBoxErrorChecker:
    def __init__(self):
        rospy.init_node('bbox_error_checker', anonymous=True)

        # 数据存储
        self.pose = None
        self.twist = None
        self.bboxes = None

        self.dist_errors = []
        self.speed_errors = []

        # 订阅话题
        rospy.Subscriber("/vrpn_client_node/P1/pose", PoseStamped, self.pose_callback)
        rospy.Subscriber("/vrpn_client_node/P1/twist", TwistStamped, self.twist_callback)
        rospy.Subscriber("/onboard_detector/dynamic_bboxes", MarkerArray, self.bbox_callback)

        # 循环执行检查函数
        rospy.Timer(rospy.Duration(0.0333), self.check_in_box)  # 10Hz

    def pose_callback(self, msg):
        self.pose = msg.pose

    def twist_callback(self, msg):
        self.twist = msg.twist

    def bbox_callback(self, msg):
        self.bboxes = msg.markers

    def point_in_bbox(self, point, bbox_points):
        # 简单用 Axis-Aligned Bounding Box (AABB) 判断是否在框内
        xs = [p.x for p in bbox_points]
        ys = [p.y for p in bbox_points]
        zs = [p.z for p in bbox_points]
        return (min(xs) <= point.x <= max(xs) and
                min(ys) <= point.y <= max(ys) and
                min(zs) <= point.z <= max(zs))

    def xy_plane_distance_to_bbox(self, point, bbox_points):
        # 计算点到每个框点的 xy 平面距离，返回最小值
        dists = [np.hypot(point.x - p.x, point.y - p.y) for p in bbox_points]
        return min(dists) if dists else float("0")

    def get_bbox_velocity_from_text(self, text):
        try:
            parts = text.strip().split()
            vx = float(parts[1])
            vy = float(parts[3])
            return vx, vy
        except Exception as e:
            rospy.logwarn("无法解析速度文本: {}，错误: {}".format(text, e))
            return 0.0, 0.0

    def check_in_box(self, event):
        if self.pose is None or self.twist is None or self.bboxes is None:
            return

        pose_point = self.pose.position
        in_any_box = False

        for marker in self.bboxes:
            if len(marker.points) == 0:
                continue
            if self.point_in_bbox(pose_point, marker.points):
                in_any_box = True
                self.dist_errors.append(0)
                break

        if not in_any_box:
            valid_dists = []
            for marker in self.bboxes:
                if len(marker.points) == 0:
                    continue
                dist = self.xy_plane_distance_to_bbox(pose_point, marker.points)
                valid_dists.append(dist)

            if valid_dists:
                min_dist = min(valid_dists)
                # rospy.loginfo(f"[误差] 点不在检测框中，最近 xy 平面距离: {min_dist:.3f} 米")
                self.dist_errors.append(min_dist)
            else:
                rospy.logwarn("[警告] 没有有效的检测框点用于误差计算！")

        if self.dist_errors:
            avg_dist = np.mean(self.dist_errors)
            rospy.loginfo(f"[平均位置误差] 当前平均误差: {avg_dist:.3f} 米")

        # —— 速度误差计算，带异常检测（阈值：2 m/s） ——
        valid_speed_errors = []
        for marker in self.bboxes:
            vx_box, vy_box = self.get_bbox_velocity_from_text(marker.text)
            v_mag = np.sqrt(vx_box**2 + vy_box**2)

            if v_mag > 2.0:
                rospy.logwarn(f"[异常速度] 忽略检测框速度 Vx={vx_box:.2f}, Vy={vy_box:.2f}，模长={v_mag:.2f}")
                continue

            vx_gt = self.twist.linear.x
            vy_gt = self.twist.linear.y

            speed_error = np.sqrt((vx_box - vx_gt) ** 2 + (vy_box - vy_gt) ** 2)
            valid_speed_errors.append(speed_error)

            # rospy.loginfo(f"[速度误差] 检测 Vx={vx_box:.2f}, Vy={vy_box:.2f} | 真值 Vx={vx_gt:.2f}, Vy={vy_gt:.2f} | 误差: {speed_error:.3f}")

        if valid_speed_errors:
            self.speed_errors.extend(valid_speed_errors)
            avg_speed_error = np.mean(self.speed_errors)
            rospy.loginfo(f"[平均速度误差] 当前平均误差: {avg_speed_error:.3f} m/s")
        else:
            rospy.loginfo("[速度误差] 当前无有效数据用于计算平均速度误差")

if __name__ == "__main__":
    try:
        BBoxErrorChecker()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
