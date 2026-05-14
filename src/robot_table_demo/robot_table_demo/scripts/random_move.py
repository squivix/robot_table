#!/usr/bin/env python3
import random
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    MotionPlanRequest, PlanningOptions,
    Constraints, PositionConstraint, OrientationConstraint,
    BoundingVolume
)
from geometry_msgs.msg import PoseStamped, Quaternion, Vector3
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import Header
import numpy as np

def random_quaternion():
    # Shoemake's method for uniform random quaternion
    u1, u2, u3 = random.random(), random.random(), random.random()
    return Quaternion(
        x=float(np.sqrt(1-u1) * np.sin(2*np.pi*u2)),
        y=float(np.sqrt(1-u1) * np.cos(2*np.pi*u2)),
        z=float(np.sqrt(u1)   * np.sin(2*np.pi*u3)),
        w=float(np.sqrt(u1)   * np.cos(2*np.pi*u3))
    )

def build_goal(x, y, z, q):
    target = PoseStamped()
    target.header = Header(frame_id='world')
    target.pose.position.x = x
    target.pose.position.y = y
    target.pose.position.z = z
    target.pose.orientation = q

    sphere = SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.01])
    pos_con = PositionConstraint(
        header=target.header,
        link_name='ur5e_tool0',
        target_point_offset=Vector3(),
        constraint_region=BoundingVolume(
            primitives=[sphere],
            primitive_poses=[target.pose]
        ),
        weight=1.0
    )

    ori_con = OrientationConstraint(
        header=target.header,
        link_name='ur5e_tool0',
        orientation=target.pose.orientation,
        absolute_x_axis_tolerance=0.1,
        absolute_y_axis_tolerance=0.1,
        absolute_z_axis_tolerance=0.1,
        weight=1.0
    )

    plan_request = MotionPlanRequest(
        group_name='ur5e_arm',
        num_planning_attempts=2,
        allowed_planning_time=1.0,
        max_velocity_scaling_factor=0.5,
        max_acceleration_scaling_factor=0.5,
        goal_constraints=[Constraints(
            position_constraints=[pos_con],
            orientation_constraints=[ori_con]
        )]
    )

    return MoveGroup.Goal(
        request=plan_request,
        planning_options=PlanningOptions(plan_and_execute=True)
    )


def main():
    rclpy.init()
    node = Node('random_pose_mover')
    client = ActionClient(node, MoveGroup, '/move_action')

    node.get_logger().info('Waiting for /move_action server...')
    client.wait_for_server()

    x = random.uniform(-0.5, 0.5)
    y = random.uniform(-0.5, 0.5)
    z = random.uniform(0.95, 1.5)
    q = random_quaternion()
    q = Quaternion(x=-0.218, y=-0.361, z=0.821, w=0.384)
    node.get_logger().info(f'Trying x={x:.2f} y={y:.2f} z={z:.2f}')

    goal = build_goal(x, y, z, q)
    future = client.send_goal_async(goal)
    rclpy.spin_until_future_complete(node, future)

    goal_handle = future.result()
    if not goal_handle.accepted:
        node.get_logger().error('Goal rejected by MoveIt')
    else:
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(node, result_future)
        error_code = result_future.result().result.error_code.val
        if error_code == 1:
            node.get_logger().info('SUCCESS - move complete')
        else:
            node.get_logger().error(f'FAILED - error_code={error_code}')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()