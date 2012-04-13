#! /usr/bin/python
        
import numpy as np
import scipy.stats as stats
import copy
import sys
from threading import Lock

import roslib
roslib.load_manifest('hrl_generic_arms')
roslib.load_manifest('hrl_ellipsoidal_control')
roslib.load_manifest('hrl_pr2_arms')

import rospy
import tf
import actionlib
from geometry_msgs.msg import PoseStamped
from std_srvs.srv import Empty
import tf.transformations as tf_trans

from hrl_generic_arms.ep_trajectory_controller import EPTrajectoryControl, min_jerk_traj
from equilibrium_point_control.ep_control import EPC, EPStopConditions
from ellipsoid_space import EllipsoidSpace
from msg import EllipsoidMoveAction, EllipsoidMoveResult
from msg import EllipsoidParams
from hrl_pr2_arms.pr2_arm import create_pr2_arm, PR2ArmCartesianBase, PR2ArmJTransposeTask
from hrl_generic_arms.pose_converter import PoseConverter
from hrl_pr2_arms.pr2_controller_switcher import ControllerSwitcher

MIN_HEIGHT = 0.2

# TODO Figure this out sometime...
#def get_time_traj(kin, dense_traj, q_start, velocity):
#    max_ang_diff = np.array([0.] * kin.n_jts)
#    q_cur = np.array(q_start)
#    for pos, rot in dense_traj:
#        q_next = np.array(kin.IK(pos, rot, q_cur))
#        cur_diff = np.fabs(q_next - q_cur)
#        max_ang_diff = np.where(cur_diff > max_ang_diff, cur_diff, max_ang_diff)
#        q_cur = q_next

class CartesianController(object):
    def __init__(self, arm):
        self.time_step = 1. / 20.
        self.arm = arm
        self.ell_traj_behavior = EPC("ellipsoid_traj")
        self.ell_space = EllipsoidSpace(1)
        self.tf_list = tf.TransformListener()
        self.found_params = False
        self.ctrl_switcher = ControllerSwitcher()
        self.cart_cmd_lock = Lock()
        self.params_lock = Lock()
        self.action_preempted = False
        self.ell_sub = rospy.Subscriber("/ellipsoid_params", EllipsoidParams, self.read_params)
        self.start_pub = rospy.Publisher("/start_pose", PoseStamped)
        self.end_pub = rospy.Publisher("/end_pose", PoseStamped)
        self.ell_move_act = actionlib.SimpleActionServer("/ellipsoid_move", EllipsoidMoveAction, 
                                                         self.command_move_exec, False)
        self.ell_move_act.start()

    def read_params(self, e_params):
        with self.params_lock:
            self.ell_space.load_ell_params(e_params)
            self.ell_space.center = np.mat(np.zeros((3, 1)))
            self.ell_space.rot = np.mat(np.eye(3))
            if not self.found_params:
                rospy.loginfo("[cartesian_controller] Found params from /ellipsoid_params")
            self.found_params = True
    
    def get_ell_ep(self):
        ee_pose = PoseConverter.to_pose_stamped_msg("/torso_lift_link", self.arm.get_ep())
        cur_time = rospy.Time.now()
        ee_pose.header.stamp = cur_time
        self.tf_list.waitForTransform("/torso_lift_link", "/ellipse_frame", cur_time, rospy.Duration(3))
        ell_pose = self.tf_list.transformPose("/ellipse_frame", ee_pose)
        pos, quat = PoseConverter.to_pos_quat(ell_pose)
        return list(self.ell_space.pos_to_ellipsoidal(*pos))

    ##
    # Get pose in robot's frame of ellipsoidal coordinates
    def robot_ellipsoidal_pose(self, lat, lon, height, orient_quat, ell_frame_mat=None):
        if ell_frame_mat is None:
            ell_frame_mat = self.get_ell_frame()
        pos, quat = self.ell_space.ellipsoidal_to_pose(lat, lon, height)
        quat_rotated = tf_trans.quaternion_multiply(quat, orient_quat)
        ell_pose_mat = PoseConverter.to_homo_mat(pos, quat_rotated)
        return PoseConverter.to_pos_rot(ell_frame_mat * ell_pose_mat)
                                          
    def reset_arm_orientation(self, duration=10., gripper_rot=np.pi):
        with self.params_lock:
            with self.cart_cmd_lock:
                num_samps = duration / self.time_step
                cur_pose = self.arm.get_end_effector_pose()
                quat_gripper_rot = tf_trans.quaternion_from_euler(gripper_rot, 0, 0)
                args = self.get_ell_ep() + [quat_gripper_rot]
                ell_pose = self.robot_ellipsoidal_pose(*args)
                adjust_traj = self.arm.interpolate_ep(cur_pose, ell_pose, 
                                                      min_jerk_traj(num_samps))
                ep_traj_control = EPTrajectoryControl(self.arm, adjust_traj)
                self.start_pub.publish(
                        PoseConverter.to_pose_stamped_msg("/torso_lift_link", cur_pose))
                self.end_pub.publish(
                        PoseConverter.to_pose_stamped_msg("/torso_lift_link", ell_pose))
                self.ell_traj_behavior.epc_motion(ep_traj_control, self.time_step)

    def command_stop(self):
        self.ell_traj_behavior.stop_epc = True

    def command_move_exec(self, req):
        if req.reset_ellipsoid:
            self.reset_arm_orientation()
        change_ep = np.array([req.change_latitude, req.change_longitude, 
                              req.change_height])
        abs_ep_sel = np.array([req.absolute_latitude, req.absolute_longitude, 
                               req.absolute_height])
        rospy.loginfo("Commanding ellipsoidal move: (%f, %f, %f), Abs: (%d, %d, %d)" % 
                       (change_ep[0], change_ep[1], change_ep[2], 
                        abs_ep_sel[0], abs_ep_sel[1], abs_ep_sel[2]))
        self.execute_ell_move(change_ep, abs_ep_sel, req.gripper_rot, req.velocity)
        self.ell_move_act.set_succeeded(EllipsoidMoveResult(*self.get_ell_ep()))

    def execute_cart_move(self, change_ep, abs_sel, orient_quat=[0., 0., 0., 1.], velocity=0.001):
        with self.params_lock:
            with self.cart_cmd_lock:
                cur_pos, cur_rot = self.arm.get_ep()
                change_pos_ep, change_rot_ep = change_ep
                abs_cart_ep_sel, is_abs_rot = abs_sel
                pos_f = np.where(abs_cart_ep_sel, change_pos_ep, 
                                 np.array(cur_pos + cur_rot * np.mat(change_pos_ep).T).T[0])
                if is_abs_rot:
                    # TODO FIX THIS
                    rot_change_mat = change_rot_ep
                    _, ell_final_rot = self.robot_ellipsoidal_pose(ell_f[0], ell_f[1], ell_f[2],
                                                                   orient_quat)
                    rot_mat_f = ell_final_rot * rot_change_mat
                else:
                    rpy = change_rot_ep
                    _, cur_rot = self.arm.get_ep()
                    rot_mat = np.mat(tf_trans.euler_matrix(*rpy))[:3,:3]
                    rot_mat_f = cur_rot * rot_mat
                self._execute_trajectory(pos_f, rot_mat_f, orient_quat, velocity)

    def _check_preempt(self, timer_event):
        if self.ell_move_act.is_preempt_requested():
            self.ell_traj_behavior.stop_epc = True
            self.action_preempted = True

    def get_ell_frame(self):
        # find the current ellipsoid frame
        cur_time = rospy.Time.now()
        self.tf_list.waitForTransform("/torso_lift_link", "/ellipse_frame", 
                                      cur_time, rospy.Duration(3))
        ell_frame_mat = PoseConverter.to_homo_mat(
                             self.tf_list.lookupTransform("/torso_lift_link", 
                                                          "/ellipse_frame", cur_time))
        return ell_frame_mat

    def _execute_trajectory(self, pos_f, rot_mat_f, orient_quat=[0., 0., 0., 1.], velocity=0.001):
        cur_pos, cur_rot = self.arm.get_ep()

        rpy = tf_trans.euler_from_matrix(cur_rot.T * rot_mat_f) # get roll, pitch, yaw of angle diff

        num_samps = np.max([2, int(np.linalg.norm(pos_f - cur_pos) / velocity), 
                               int(np.linalg.norm(rpy) / velocity)])

        ell_frame_mat = self.get_ell_frame()

        traj = self.arm.interpolate_ep([cur_pos, cur_rot], 
                                       [np.mat(pos_f).T, rot_mat_f], 
                                       min_jerk_traj(num_samps))

        self.start_pub.publish(
                PoseConverter.to_pose_stamped_msg("/torso_lift_link", traj[0]))
        self.end_pub.publish(
                PoseConverter.to_pose_stamped_msg("/torso_lift_link", traj[-1]))
        ep_traj_control = EPTrajectoryControl(self.arm, traj)
        self.action_preempted = False
        self.ell_traj_behavior.stop_epc = False
        monitor_timer = rospy.Timer(rospy.Duration(0.1), self._check_preempt)
        self.ell_traj_behavior.epc_motion(ep_traj_control, self.time_step)
        monitor_timer.shutdown()
        if self.action_preempted:
            pass

def main():
    rospy.init_node("cartesian_controller", sys.argv)
    cart_arm = create_pr2_arm('l', PR2ArmJTransposeTask, 
                              controller_name='%s_cart_jt_task', 
                              end_link="%s_gripper_shaver45_frame", timeout=0)

    rospy.sleep(1)
    cart_controller = CartesianController(cart_arm)
    rospy.spin()
    

if __name__ == "__main__":
    main()
