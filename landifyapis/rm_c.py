import os


def remove_comments_from_file(filepath):
    """
    Xóa các comment một dòng (#) khỏi một file Python,
    đảm bảo không xóa dấu # bên trong các chuỗi (string literals).
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            new_line_chars = []
            in_single_quote_string = False  # Theo dõi nếu đang ở trong chuỗi '...'
            in_double_quote_string = False  # Theo dõi nếu đang ở trong chuỗi "..."
            escape_char_next = False  # Theo dõi ký tự thoát (ví dụ: '\#')

            for char_index, char in enumerate(line):
                if escape_char_next:
                    # Nếu ký tự trước là '\', thì ký tự hiện tại được thoát
                    new_line_chars.append(char)
                    escape_char_next = False
                    continue

                if char == '\\':
                    # Phát hiện ký tự thoát, đánh dấu để bỏ qua kiểm tra comment cho ký tự tiếp theo
                    escape_char_next = True
                    new_line_chars.append(char)
                    continue

                if char == "'":
                    if not in_double_quote_string:
                        # Chuyển đổi trạng thái khi gặp dấu nháy đơn, nếu không ở trong chuỗi nháy kép
                        in_single_quote_string = not in_single_quote_string
                    new_line_chars.append(char)
                elif char == '"':
                    if not in_single_quote_string:
                        # Chuyển đổi trạng thái khi gặp dấu nháy kép, nếu không ở trong chuỗi nháy đơn
                        in_double_quote_string = not in_double_quote_string
                    new_line_chars.append(char)
                elif char == '#':
                    if not in_single_quote_string and not in_double_quote_string:
                        # Phát hiện comment bên ngoài chuỗi, cắt bỏ phần còn lại của dòng
                        break
                    else:
                        # Dấu # nằm trong chuỗi, giữ lại
                        new_line_chars.append(char)
                else:
                    new_line_chars.append(char)

            # Nối các ký tự lại thành một dòng mới và loại bỏ khoảng trắng thừa ở cuối trước khi thêm ký tự xuống dòng
            new_lines.append("".join(new_line_chars).rstrip() + '\n')

        # Ghi nội dung đã sửa đổi trở lại file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"Đã xử lý: {filepath}")
    except Exception as e:
        print(f"Lỗi khi xử lý {filepath}: {e}")


def process_directory(directory_path):
    """
    Duyệt qua thư mục đã cho và xóa comment khỏi tất cả các file .py.
    """
    if not os.path.isdir(directory_path):
        print(f"Lỗi: '{directory_path}' không phải là một thư mục hợp lệ.")
        return

    print(f"Bắt đầu xử lý thư mục: {directory_path}")
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                remove_comments_from_file(filepath)
    print(f"Hoàn thành xử lý thư mục: {directory_path}")


if __name__ == "__main__":
    print("--- Script xóa comments trong các file .py ---")
    print("Lưu ý: Script này chỉ xóa các comment bắt đầu bằng '#' và không xóa docstrings (chuỗi đa dòng).")
    print("Vui lòng sao lưu thư mục của bạn trước khi chạy script này để tránh mất dữ liệu không mong muốn.")
    print("-" * 40)

    input_directory = input("Nhập đường dẫn thư mục cần xử lý (ví dụ: C:\\MyProject hoặc /home/user/my_project): ")

    # Xử lý trường hợp người dùng nhập đường dẫn có dấu nháy kép thừa
    input_directory = input_directory.strip().strip('"').strip("'")

    process_directory(input_directory)
    print("\nQuá trình hoàn tất!")