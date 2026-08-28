#include <rclcpp/rclcpp.hpp>
#include <moveit/move_group_interface/move_group_interface.h>
#include <moveit/planning_scene_interface/planning_scene_interface.h>
#include <geometry_msgs/msg/pose.hpp>
#include <random>

class SetTargetPosition : public rclcpp::Node
{
public:
  SetTargetPosition()
    : Node("set_target_position")
  {
    // 初始化其他内容
    RCLCPP_INFO(this->get_logger(), "Initializing RandomMoveIt2Control.");
  }

  void initialize()
  {
    // 在此函数中初始化 move_group_interface_ 和 planning_scene_interface_
    move_group_interface_ = std::make_shared<moveit::planning_interface::MoveGroupInterface>(shared_from_this(), "arm_group");
    planning_scene_interface_ = std::make_shared<moveit::planning_interface::PlanningSceneInterface>();

    move_group_interface_->setNumPlanningAttempts(10);  // 设置最大规划尝试次数为 10
    move_group_interface_->setPlanningTime(5.0);         // 设置每次规划的最大时间为 5 秒
    // 设置随机数生成器
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<> dis(-0.1, 0.1);
    // 规划路径
    moveit::planning_interface::MoveGroupInterface::Plan my_plan;
    
    move_group_interface_->setNamedTarget("up");
    bool success = (move_group_interface_->plan(my_plan) == moveit::core::MoveItErrorCode::SUCCESS);
    if (success)
    {
    	RCLCPP_INFO(this->get_logger(), "Init arm successed.");
    	move_group_interface_->execute(my_plan);
    }
    else
    {
    	RCLCPP_ERROR(this->get_logger(), "Init arm failed!");
    }
      geometry_msgs::msg::PoseStamped pose_up = move_group_interface_->getPoseTarget();
      RCLCPP_INFO(this->get_logger(), "pose_up: position.x=%f, position.y=%f, position.z=%f, orientation.x=%f, orientation.y=%f, orientation.z=%f, orientation.w=%f" ,
                    pose_up.pose.position.x,
                    pose_up.pose.position.y,
                    pose_up.pose.position.z,
                    pose_up.pose.orientation.x,
                    pose_up.pose.orientation.y,
                    pose_up.pose.orientation.z,
                    pose_up.pose.orientation.w);
    
    //std::vector<double> target_joints = {0.79, 0.79, -1.57, -1.57, 0}; // 目标关节角度（单位：弧度）

        // 设置目标关节空间值
    //move_group_interface_->setJointValueTarget(target_joints);
    // 设置目标位置
    geometry_msgs::msg::Pose target_pose;

    // pose4
    // target_pose.orientation.x = 0.147677;
    // target_pose.orientation.y = 0.0169656;
    // target_pose.orientation.z = 0.35477;
    // target_pose.orientation.w = 4.01632;
    // target_pose.position.x = -8.73571;
    // target_pose.position.y = 2.15294;
    // target_pose.position.z = 1;
    target_pose.position.x = 0.13695764541625977;
    target_pose.position.y = -0.005238924641162157;
    target_pose.position.z = 0.3486359715461731;
    target_pose.orientation.x = 3.1805826438358054e-05;
    target_pose.orientation.y = -4.311262455303222e-05;
    target_pose.orientation.z = -3.6135115806246176e-05;
    target_pose.orientation.w = 1;

    // 设置目标位置
    move_group_interface_->setPoseTarget(target_pose);


    bool success_position = (move_group_interface_->plan(my_plan) == moveit::core::MoveItErrorCode::SUCCESS);

    if (success_position)
    {
      RCLCPP_INFO(this->get_logger(), "Planning succeeded, moving the arm.");
      move_group_interface_->execute(my_plan);
      rclcpp::sleep_for(std::chrono::seconds(5));
            // 获取当前机械臂末端的位姿
      geometry_msgs::msg::PoseStamped pose_target = move_group_interface_->getPoseTarget();

      RCLCPP_INFO(this->get_logger(), "pose_target: position.x=%f, position.y=%f, position.z=%f, orientation.x=%f, orientation.y=%f, orientation.z=%f, orientation.w=%f" ,
                    pose_target.pose.position.x,
                    pose_target.pose.position.y,
                    pose_target.pose.position.z,
                    pose_target.pose.orientation.x,
                    pose_target.pose.orientation.y,
                    pose_target.pose.orientation.z,
                    pose_target.pose.orientation.w);
    }
    else
    {
      RCLCPP_ERROR(this->get_logger(), "Planning failed!");
    }

  }

private:
  std::shared_ptr<moveit::planning_interface::MoveGroupInterface> move_group_interface_;
  std::shared_ptr<moveit::planning_interface::PlanningSceneInterface> planning_scene_interface_;
};

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<SetTargetPosition>();
  
  // 延迟初始化
  node->initialize();

  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
