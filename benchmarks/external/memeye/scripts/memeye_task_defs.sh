# Shared task names for MemEye 8-scenario benchmark (MCQ + mirrored Open).
MEMEYE_TASKS=(
  brand_memory_test
  card_playlog_test
  cartoon_entertainment_companion
  home_renovation_interior_design
  multi_scene_visual_case_archive_assistant
  outdoor_navigation_route_memory_assistant
  personal_health_dashboard_assistant
  social_chat_memory_test
)

memeye_mcq_dialog() {
  case "$1" in
    brand_memory_test) echo "Brand_Memory_Test.json" ;;
    card_playlog_test) echo "Card_Playlog_Test.json" ;;
    cartoon_entertainment_companion) echo "Cartoon_Entertainment_Companion.json" ;;
    home_renovation_interior_design) echo "Home_Renovation_Interior_Design.json" ;;
    multi_scene_visual_case_archive_assistant) echo "Multi-Scene_Visual_Case_Archive_Assistant.json" ;;
    outdoor_navigation_route_memory_assistant) echo "Outdoor_Navigation_Route_Memory_Assistant.json" ;;
    personal_health_dashboard_assistant) echo "Personal_Health_Dashboard_Assistant.json" ;;
    social_chat_memory_test) echo "Social_Chat_Memory_Test.json" ;;
    *) return 1 ;;
  esac
}

memeye_open_dialog() {
  case "$1" in
    brand_memory_test) echo "Brand_Memory_Test_Open.json" ;;
    card_playlog_test) echo "Card_Playlog_Test_Open.json" ;;
    cartoon_entertainment_companion) echo "Cartoon_Entertainment_Companion_Open.json" ;;
    home_renovation_interior_design) echo "Home_Renovation_Interior_Design_Open.json" ;;
    multi_scene_visual_case_archive_assistant) echo "Multi-Scene_Visual_Case_Archive_Assistant_Open.json" ;;
    outdoor_navigation_route_memory_assistant) echo "Outdoor_Navigation_Route_Memory_Assistant_Open.json" ;;
    personal_health_dashboard_assistant) echo "Personal_Health_Dashboard_Assistant_Open.json" ;;
    social_chat_memory_test) echo "Social_Chat_Memory_Test_Open.json" ;;
    *) return 1 ;;
  esac
}
