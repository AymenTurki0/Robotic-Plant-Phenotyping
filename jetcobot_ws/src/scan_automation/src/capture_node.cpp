#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <std_msgs/msg/int32.hpp>
#include <std_msgs/msg/float64.hpp>
#include <cv_bridge/cv_bridge.hpp>
#include <opencv2/opencv.hpp>
#include <opencv2/highgui.hpp>
#include <fstream>
#include <filesystem>
#include <mutex>
#include <thread>
#include <atomic>
#include <chrono>

// Captures ONE frame per /capture_signal message, and only replies with an
// ack once the frame (and its metadata) is actually on disk. sequence_node
// blocks on that ack before commanding the next motion, so there is never
// more than one capture in flight and the arm is guaranteed to be at rest
// (frame is grabbed the instant the request arrives; sequence_node only
// sends the request after its own settle delay).
class CaptureNode : public rclcpp::Node
{
public:
  CaptureNode() : Node("capture_node"), running_(false), start_scan_(false),
                   auto_started_(false), captured_count_(0), turntable_deg_(0.0)
  {
    this->declare_parameter<std::string>("dataset_path", std::string(getenv("HOME")) + "/scan_dataset");
    // If false: no OpenCV window/thread at all -- required for headless runs
    // (SSH, no X server, CI, etc). Scan is instead kicked off automatically
    // (see auto_start / auto_start_delay_s) or by publishing to
    // /capture_start yourself.
    this->declare_parameter<bool>("show_preview", true);
    this->declare_parameter<bool>("auto_start", false);
    this->declare_parameter<double>("auto_start_delay_s", 2.0);
    // Stale-frame guard: if the newest image is older than this when a
    // capture request arrives, we log a warning (and retry a few times)
    // instead of silently saving a frame from before the settle.
    this->declare_parameter<double>("max_frame_age_s", 0.5);
    // Optional camera intrinsics, written once to camera_intrinsics.yaml
    // if provided, so the dataset is self-contained for the reconstruction
    // step. Leave at 0 to skip.
    this->declare_parameter<double>("fx", 0.0);
    this->declare_parameter<double>("fy", 0.0);
    this->declare_parameter<double>("cx", 0.0);
    this->declare_parameter<double>("cy", 0.0);

    this->get_parameter("dataset_path", output_dir_);
    this->get_parameter("show_preview", show_preview_);
    this->get_parameter("auto_start", auto_start_);
    this->get_parameter("auto_start_delay_s", auto_start_delay_s_);
    this->get_parameter("max_frame_age_s", max_frame_age_s_);

    std::filesystem::create_directories(output_dir_);
    RCLCPP_INFO(this->get_logger(), "Dataset directory: %s", output_dir_.c_str());
    write_intrinsics_if_provided();

    img_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
      "/camera/image_raw", 10, std::bind(&CaptureNode::image_cb, this, std::placeholders::_1));
    joint_sub_ = this->create_subscription<sensor_msgs::msg::JointState>(
      "/joint_states", 10, std::bind(&CaptureNode::joint_cb, this, std::placeholders::_1));
    turntable_angle_sub_ = this->create_subscription<std_msgs::msg::Float64>(
      "/turntable/current_angle_deg", 10, std::bind(&CaptureNode::turntable_angle_cb, this, std::placeholders::_1));

    start_pub_ = this->create_publisher<std_msgs::msg::Int32>("/capture_start", 10);
    capture_sub_ = this->create_subscription<std_msgs::msg::Int32>(
      "/capture_signal", 10, std::bind(&CaptureNode::capture_cb, this, std::placeholders::_1));
    capture_ack_pub_ = this->create_publisher<std_msgs::msg::Int32>("/capture_ack", 10);

    if (show_preview_) {
      gui_thread_ = std::thread(&CaptureNode::gui_loop, this);
    } else {
      RCLCPP_INFO(this->get_logger(), "show_preview=false -- running headless, no GUI window.");
    }

    if (auto_start_) {
      auto_start_timer_ = this->create_wall_timer(
        std::chrono::duration<double>(auto_start_delay_s_),
        std::bind(&CaptureNode::auto_start_cb, this));
    }
  }

  ~CaptureNode() {
    running_ = false;
    if (gui_thread_.joinable()) gui_thread_.join();
    if (show_preview_) cv::destroyAllWindows();
  }

private:
  void auto_start_cb() {
    if (auto_started_.exchange(true)) return;
    auto_start_timer_->cancel();
    std_msgs::msg::Int32 msg;
    msg.data = 0;
    start_pub_->publish(msg);
    RCLCPP_INFO(this->get_logger(), "auto_start: scan start signal sent.");
  }

  void write_intrinsics_if_provided() {
    double fx, fy, cx, cy;
    this->get_parameter("fx", fx);
    this->get_parameter("fy", fy);
    this->get_parameter("cx", cx);
    this->get_parameter("cy", cy);
    if (fx == 0.0 && fy == 0.0 && cx == 0.0 && cy == 0.0) return; // not provided
    std::ofstream f(output_dir_ + "/camera_intrinsics.yaml");
    f << "fx: " << fx << "\nfy: " << fy << "\ncx: " << cx << "\ncy: " << cy << "\n";
  }

  void image_cb(const sensor_msgs::msg::Image::SharedPtr msg) {
    std::lock_guard<std::mutex> lock(data_mutex_);
    try {
      latest_frame_ = cv_bridge::toCvShare(msg, "bgr8")->image.clone();
      latest_frame_stamp_ = this->now();
    } catch (cv_bridge::Exception& e) {
      RCLCPP_ERROR(this->get_logger(), "cv_bridge exception: %s", e.what());
    }
  }

  void joint_cb(const sensor_msgs::msg::JointState::SharedPtr msg) {
    std::lock_guard<std::mutex> lock(data_mutex_);
    latest_joints_ = msg->position;
    joint_names_ = msg->name;
  }

  void turntable_angle_cb(const std_msgs::msg::Float64::SharedPtr msg) {
    turntable_deg_ = msg->data;
  }

  void capture_cb(const std_msgs::msg::Int32::SharedPtr msg) {
    int index = msg->data;

    if (index == -1) {
      RCLCPP_INFO(this->get_logger(), "Scan complete! Shutting down...");
      write_manifest_footer();
      rclcpp::shutdown();
      return;
    }

    // Grab whatever the latest frame is right now -- no waiting, no
    // retries. Continuous capture means there's always a fresh-enough
    // frame in flight; blocking here would just add lag to the interval.
    cv::Mat frame_copy;
    std::vector<double> joints_copy;
    std::vector<std::string> names_copy;
    {
      std::lock_guard<std::mutex> lock(data_mutex_);
      if (latest_frame_.empty()) {
        RCLCPP_WARN(this->get_logger(), "No image available yet for frame %d -- skipping.", index);
        ack(index);
        return;
      }
      frame_copy = latest_frame_.clone();
      joints_copy = latest_joints_;
      names_copy = joint_names_;
      double age = (this->now() - latest_frame_stamp_).seconds();
      if (age > max_frame_age_s_) {
        RCLCPP_WARN(this->get_logger(), "Frame %d: image is %.2fs old (> %.2fs) -- saving anyway.",
          index, age, max_frame_age_s_);
      }
    }

    std::string img_path = output_dir_ + "/frame_" + std::to_string(index) + ".png";
    if (!cv::imwrite(img_path, frame_copy)) {
      RCLCPP_ERROR(this->get_logger(), "Failed to write %s", img_path.c_str());
    }

    std::string yaml_path = output_dir_ + "/frame_" + std::to_string(index) + ".yaml";
    std::ofstream yaml_file(yaml_path);
    yaml_file << "frame_index: " << index << "\n";
    yaml_file << "turntable_angle_deg: " << turntable_deg_ << "\n";
    yaml_file << "joints:\n";
    for (size_t i = 0; i < joints_copy.size(); ++i) {
      yaml_file << "  - name: " << (i < names_copy.size() ? names_copy[i] : "unknown") << "\n";
      yaml_file << "    position: " << joints_copy[i] << "\n";
    }
    yaml_file.close();

    append_manifest_line(index, img_path, yaml_path);

    captured_count_++;
    RCLCPP_INFO(this->get_logger(), "[SAVED] Frame #%d (turntable %.1f deg, total: %d)",
      index, turntable_deg_.load(), captured_count_.load());

    ack(index);
  }

  void ack(int index) {
    std_msgs::msg::Int32 ack_msg;
    ack_msg.data = index;
    capture_ack_pub_->publish(ack_msg);
  }

  void append_manifest_line(int index, const std::string& img_path, const std::string& yaml_path) {
    std::lock_guard<std::mutex> lock(manifest_mutex_);
    std::ofstream manifest(output_dir_ + "/manifest.csv", std::ios::app);
    manifest << index << "," << img_path << "," << yaml_path << "," << turntable_deg_ << "\n";
  }

  void write_manifest_footer() {
    std::ofstream f(output_dir_ + "/manifest_done.txt");
    f << "total_frames: " << captured_count_.load() << "\n";
  }

  void gui_loop() {
    running_ = true;
    cv::namedWindow("Robot Camera & Control", cv::WINDOW_NORMAL);
    cv::resizeWindow("Robot Camera & Control", 800, 600);

    cv::createButton("START SCAN", button_callback, this, cv::QT_PUSH_BUTTON, 0);

    RCLCPP_INFO(this->get_logger(), "GUI ready - Click 'START SCAN' button when ready");

    while (running_ && rclcpp::ok()) {
      cv::Mat display_frame;
      {
        std::lock_guard<std::mutex> lock(data_mutex_);
        if (!latest_frame_.empty()) display_frame = latest_frame_.clone();
      }

      if (!display_frame.empty()) {
        std::string status = start_scan_ ? "STARTING SCAN..." : "READY - Click START";
        cv::putText(display_frame, status, cv::Point(10, 30),
                    cv::FONT_HERSHEY_SIMPLEX, 0.8, cv::Scalar(0, 255, 0), 2);
        if (captured_count_ > 0) {
          cv::putText(display_frame, "Captured: " + std::to_string(captured_count_),
                      cv::Point(10, 60), cv::FONT_HERSHEY_SIMPLEX, 0.6, cv::Scalar(255, 255, 0), 2);
        }
        cv::imshow("Robot Camera & Control", display_frame);
      }

      int key = cv::waitKey(30);
      if (key == 27) {
        RCLCPP_INFO(this->get_logger(), "ESC pressed - shutting down");
        rclcpp::shutdown();
        break;
      }

      if (start_scan_.exchange(false)) {
        std_msgs::msg::Int32 start_msg;
        start_msg.data = 0;
        start_pub_->publish(start_msg);
        RCLCPP_INFO(this->get_logger(), "Start signal sent to sequence_node!");
      }
    }
  }

  static void button_callback(int /*state*/, void* userdata) {
    CaptureNode* node = static_cast<CaptureNode*>(userdata);
    if (node) {
      node->start_scan_ = true;
      RCLCPP_INFO(node->get_logger(), "START button clicked!");
    }
  }

  rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr img_sub_;
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_sub_;
  rclcpp::Subscription<std_msgs::msg::Float64>::SharedPtr turntable_angle_sub_;
  rclcpp::Subscription<std_msgs::msg::Int32>::SharedPtr capture_sub_;
  rclcpp::Publisher<std_msgs::msg::Int32>::SharedPtr start_pub_;
  rclcpp::Publisher<std_msgs::msg::Int32>::SharedPtr capture_ack_pub_;
  rclcpp::TimerBase::SharedPtr auto_start_timer_;

  std::mutex data_mutex_;
  std::mutex manifest_mutex_;
  cv::Mat latest_frame_;
  rclcpp::Time latest_frame_stamp_;
  std::vector<double> latest_joints_;
  std::vector<std::string> joint_names_;
  std::string output_dir_;
  std::atomic<int> captured_count_;
  std::atomic<double> turntable_deg_;

  bool show_preview_;
  bool auto_start_;
  double auto_start_delay_s_;
  double max_frame_age_s_;
  std::atomic<bool> running_;
  std::atomic<bool> start_scan_;
  std::atomic<bool> auto_started_;
  std::thread gui_thread_;
};

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<CaptureNode>();
  rclcpp::spin(node);
  return 0;
}