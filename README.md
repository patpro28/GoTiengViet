# Bộ Gõ Việt

**Gõ tự nhiên. Viết trọn ý.** Bộ gõ Telex / VNI cho Ubuntu GNOME, có cửa sổ thiết lập GTK và tích hợp IBus.

Phiên bản **0.3.2**, lấy cảm hứng từ trải nghiệm của XKey. Đây là ứng dụng Linux viết bằng Python/GTK; mã Swift dành cho macOS trong thư mục tham khảo `xkey/` không chạy trên Ubuntu. Mã bộ gõ và giao diện mới được triển khai độc lập, giấy phép MIT.

## Mở giao diện ngay

Trong thư mục dự án hoặc gói đã giải nén:

```bash
/usr/bin/python3 preferences.py
```

Không cần cài vào hệ thống để mở giao diện, thử kiểu gõ hoặc dùng công cụ chuyển văn bản. Ô **Thử một chút tiếng Việt** nhận phím gốc bằng input context đơn giản để tránh bị bộ gõ đang chọn chuyển đổi trước. Đây là phần xem trước quy tắc; IBus mới xử lý bàn phím trong các ứng dụng khác.

Nút **Đóng** ở góc dưới bên phải luôn hiển thị ngoài vùng cuộn. Thanh tiêu đề cũng có nút đóng cửa sổ. Đóng cửa sổ thiết lập vẫn để engine IBus hoạt động trong các ứng dụng.

Từ 0.3.2, màu nền, chữ, biểu tượng, ô chọn và nút cửa sổ dùng màu của theme GTK để theo chế độ sáng/tối. Ứng dụng đọc lựa chọn sáng/tối của GNOME và cập nhật GtkSettings trong tiến trình của mình khi lựa chọn đổi; không sửa thiết lập giao diện của hệ điều hành. CSS chỉ áp dụng trong cửa sổ Bộ Gõ Việt, các hộp thoại hệ thống giữ theme GTK chuẩn.

Máy cần Python 3.10+, IBus và GTK 3. Nếu thiếu thư viện:

```bash
sudo apt install ibus python3-gi gir1.2-ibus-1.0 gir1.2-gtk-3.0
```

## Có gì trong bản này?

- **Cửa sổ GTK tiếng Việt:** thanh điều hướng, trạng thái kết nối IBus, thiết lập và ô thử gõ trực tiếp.
- **Telex và VNI:** Unicode NFC, chữ hoa/thường, đặt dấu khi đã gõ phụ âm cuối, xóa theo ký tự hiển thị và Esc khôi phục phím gốc.
- **Hai cách đặt dấu:** `hòa / khỏe / thủy` hoặc `hoà / khoẻ / thuỷ`.
- **Bỏ gạch chân và nhập trực tiếp:** tắt gạch chân khi soạn từ, hoặc gửi chữ vào ứng dụng sau từng phím ở ứng dụng có hỗ trợ (thử nghiệm).
- **Gõ tắt:** thêm, sửa, xóa; mở rộng từ khi nhấn Space, Enter, Tab hoặc dấu câu. Phân biệt hoa/thường, chỉ hoạt động ở chế độ tiếng Việt. Mặc định tắt; có ba ví dụ để thử.
- **Chuyển văn bản:** bỏ dấu, CHỮ HOA, chữ thường, Hoa Đầu Từ; sao chép kết quả.
- **Sao lưu/khôi phục:** xuất và nhập thiết lập cùng danh sách gõ tắt bằng JSON có kiểm tra dữ liệu.
- **Lưu cục bộ:** cập nhật cấu hình bằng thay thế tệp nguyên tử, quyền tệp `0600`. IBus nhận thay đổi ở lần lấy focus hoặc phím tiếp theo; từ đang soạn được chốt trước khi đổi thiết lập.
- **Menu IBus:** chuyển Việt/Anh, chọn Telex/VNI và mở cửa sổ thiết lập. Có biểu tượng và mục ứng dụng sau khi cài.

Ứng dụng không gọi dịch vụ mạng và không ghi lại nội dung bạn gõ. Cấu hình chứa những từ viết tắt bạn chủ động thêm.

## Cài để gõ trong ứng dụng

```bash
sudo /usr/bin/python3 install.py
/usr/bin/python3 enable.py
```

Trình cài chép mã vào `/usr/local/share/bo-go-viet`, đăng ký `/usr/share/ibus/component/bo-go-viet.xml` và thêm `/usr/local/share/applications/bo-go-viet.desktop`. Chạy `enable.py` bằng tài khoản thường, không dùng `sudo`. Lệnh này giữ các nguồn bàn phím đang có và có thể làm mới IBus để nhận bộ gõ; hãy hoàn tất từ đang gõ trước khi chạy.

Nhấn **Super + Space**, chọn **Bộ Gõ Việt**. Mở **Bộ Gõ Việt** trong danh sách ứng dụng để đổi kiểu gõ và thiết lập. IBus tự khởi chạy engine khi được chọn; không cần thêm ứng dụng tự khởi động.

Nếu IBus chưa nhận bộ gõ, đăng xuất/đăng nhập rồi chạy lại `enable.py`. Khi nâng cấp từ bản cũ, chạy lại trình cài rồi đăng xuất/đăng nhập để thay engine đang chạy. ID `bo-go-viet-telex` được giữ để tương thích với nguồn bàn phím cũ; engine này hỗ trợ cả Telex lẫn VNI.

## Không gạch chân và nhận chữ ngay

Trong **Tổng quan** có các thiết lập:

- **Gạch chân khi soạn:** mặc định tắt từ 0.3.0. Engine gửi thuộc tính không gạch chân cho phần soạn từ; một số ứng dụng có thể tự vẽ dấu hiệu soạn thảo riêng. Tắt gạch chân vẫn giữ cơ chế soạn cả từ và chốt ở Space/Enter.
- **Cách nhập → Nhập trực tiếp · thử nghiệm:** ứng dụng nhận chữ sau từng phím. Khi gõ phím dấu, engine yêu cầu sửa phần cuối của từ vừa nhập, không hiển thị preedit trong lúc nhập trực tiếp hoạt động.
- **Cách nhập → Trực tiếp qua phím · tương thích:** dành cho ô nhập không hỗ trợ văn bản quanh con trỏ, ví dụ ô chat đã được thử trong phiên phát triển. Engine gửi phím Backspace để thay phần cuối của từ bằng chữ có dấu, không dùng vùng soạn từ. Bản 0.3.1 chờ ứng dụng xử lý phím xóa trước khi chèn chữ thay thế, và xếp các phím gõ tiếp theo đúng thứ tự để tránh lỗi như `Phamj` → `Phaạ`.

Nhập trực tiếp dùng `SURROUNDING_TEXT` và `delete_surrounding_text` của IBus. Engine chỉ sửa đúng phần văn bản vừa gửi khi ứng dụng xác nhận nội dung, vị trí con trỏ và vùng chọn khớp. Khi ứng dụng không hỗ trợ, phản hồi chưa kịp, thay đổi văn bản hoặc di chuyển con trỏ/chọn chữ, engine quay về soạn từ. Nếu việc chuyển về soạn từ xảy ra giữa từ, phần đã gửi được giữ nguyên; từ đó có thể cần gõ lại. Chế độ này không gửi Backspace giả.

**Trực tiếp qua phím** là lựa chọn riêng, không tự động bật thay cho chế độ kiểm tra văn bản. Vì ứng dụng không cung cấp nội dung quanh con trỏ, engine không thể xác minh độc lập vị trí cần sửa. Hãy nhấn Space để chốt từ trước khi bấm chuột đổi vị trí hoặc chọn chữ. Reset, phím di chuyển, phím tắt và đổi focus sẽ xóa bộ nhớ của từ; phần chèn đang chờ bị hủy khi đổi focus/reset để tránh chèn vào ô mới. Nếu đổi focus ngay giữa lượt xóa và chèn, phần cuối của từ cũ có thể cần gõ lại. Chế độ này không hoạt động trong trường mật khẩu/PIN/riêng tư được khai báo đúng.

Từ 0.3.2, Backspace thông thường trong chế độ qua phím được trả thẳng về ứng dụng: bộ gõ cập nhật bộ nhớ từ nhưng không tạo phím xóa giả hay khoảng chờ. Chỉ thao tác cần thay chữ hoặc chuyển lại vị trí dấu mới cần tuần tự xóa/chèn. Dấu cách và ký tự in được đang nằm trong hàng đợi được chèn theo cùng thứ tự văn bản, tránh dấu cách chạy chậm hơn chữ của từ tiếp theo.

**Soạn từ · tương thích** vẫn là mặc định. Nhập trực tiếp đã qua kiểm tra IBus với một client kiểm thử xử lý commit/xóa và gửi lại surrounding text; chưa bảo đảm hoạt động trực tiếp trong mọi trình duyệt, Electron hay Terminal. Ô thử kiểu gõ trong cửa sổ thiết lập chỉ xem trước quy tắc Telex/VNI, không mô phỏng khả năng nhập trực tiếp của ứng dụng khác.

Sau khi thử gõ, mở lại **Tổng quan** để xem chế độ thực tế của lần gõ gần nhất và lý do quay về soạn từ. Chẩn đoán chỉ lưu phiên bản, PID, khả năng hỗ trợ và tên chế độ/lý do trong `$XDG_RUNTIME_DIR/bo-go-viet-status.json`; không lưu phím gõ hoặc nội dung văn bản. Tham khảo API nền tảng: [IBus Engine](https://ibus.github.io/docs/ibus-1.5/IBusEngine.html).

## VS Code bị lặp chữ như `Phamạm`

Trên máy đã kiểm tra, GNOME Shell 50.1 / Mutter 50.1-0ubuntu2.5 bỏ các phím IBus gửi tới ứng dụng Wayland và ghi lỗi `clutter_event_key_new: assertion 'CLUTTER_IS_INPUT_DEVICE (source_device)' failed`. Vì phím Backspace bị bỏ, ứng dụng vẫn giữ `Pham` rồi chèn thêm `ạm`. Tăng độ trễ không khắc phục được trường hợp phím bị loại bỏ này. GNOME có [bản sửa ở Mutter](https://github.com/GNOME/mutter/commit/570de65dd05e1b362fdef90dcb811c22acd8a8e2).

Cách tránh đã kiểm tra là chạy VS Code qua X11/XWayland:

1. Lưu công việc và thoát toàn bộ cửa sổ VS Code bằng **File → Exit**.
2. Mở lại từ Terminal:

```bash
code --ozone-platform=x11
```

Giữ chế độ **Trực tiếp qua phím · tương thích** của bộ gõ. Cần thoát tiến trình VS Code cũ trước khi đổi backend, vì lệnh mở cửa sổ có thể dùng lại tiến trình đang chạy.

Trong phiên sửa lỗi này, các launcher của tài khoản đã được thêm `--ozone-platform=x11` vào `~/.local/share/applications/com.microsoft.VSCode.desktop` và `~/.local/share/applications/com.microsoft.VSCode.UrlHandler.desktop`, dựa trên launcher của gói `code` đang cài. Sau khi thoát VS Code, mở lại từ biểu tượng cũng dùng X11. Đây là thiết lập riêng trên máy, không phải thay đổi backend tự động do engine IBus thực hiện. Nếu khởi chạy bằng lệnh `code` trong Terminal, vẫn cần truyền cờ trên.

Đã mở một VS Code X11 với hồ sơ và tệp tạm riêng, gửi chuỗi `Phamj Tooi yeeu tieengs Vieetj` bằng phím XTest qua IBus thật và đọc lại tài liệu trong editor: kết quả đúng `Phạm Tôi yêu tiếng Việt`. Cửa sổ kiểm thử được đóng sau khi đọc kết quả; hồ sơ và tài liệu VS Code hiện tại của người dùng không bị chỉnh sửa. Việc xác nhận này áp dụng cho backend X11 đã thử, chưa phải xác nhận chế độ gửi phím trên Wayland có lỗi nêu trên.

Để bỏ tùy chỉnh launcher khi đã có bản sửa hệ thống phù hợp, xóa hai bản sao launcher trong thư mục tài khoản nêu trên; launcher gốc của gói vẫn nằm trong `/usr/share/applications/`.

Phạm

## Cách gõ

| Thao tác | Telex | VNI |
| --- | --- | --- |
| â, ê, ô | aa, ee, oo | a6, e6, o6 |
| ă, ơ, ư | aw, ow, uw | a8, o7, u7 |
| ươ | uow, uwow | uo7 |
| đ | dd | d9 |
| sắc, huyền, hỏi, ngã, nặng | s, f, r, x, j | 1, 2, 3, 4, 5 |
| Bỏ dấu thanh | z | 0 |
| tiếng Việt | tieengs Vieetj | tie61ng Vie65t |

| Phím | Chức năng |
| --- | --- |
| Ctrl + Shift + Space | Bật/tắt tiếng Việt; lưu trạng thái |
| Backspace | Xóa một ký tự đang hiển thị |
| Esc | Chốt chuỗi phím gốc của từ đang soạn, bỏ qua gõ tắt |
| Space, Enter, Tab, dấu câu | Chốt từ và áp dụng gõ tắt nếu bật |
| Super + Space | Chuyển nguồn bàn phím của GNOME |

Ví dụ: `dduowngf` / `d9uo72ng` → đường; `nguowif` / `nguoi72` → người. Phím dấu lặp lại được dùng để thoát dấu, ví dụ `ass` → `as` hoặc `a11` → `a1`.

Gõ tắt dùng chuỗi phím gốc làm khóa. Ví dụ thêm `camon` → `Cảm ơn bạn!`, bật gõ tắt rồi nhập `camon` và Space. Chuyển cửa sổ, nhấn phím tắt hay Esc chỉ chốt từ, không mở rộng gõ tắt. Xóa bằng Backspace sẽ biến phần còn lại thành nền văn bản mới, nên Esc sau đó khôi phục nền này. Từ đã chốt không được sửa ngược bằng Telex/VNI.

Để gõ tiếng Anh hoặc mã nguồn, dùng Ctrl + Shift + Space hoặc chuyển nguồn English. Bộ gõ chưa tự phát hiện tiếng Anh; `book` có thể thành `bôk` theo quy tắc Telex trước khi bạn nhấn Esc.

## Cấu hình và sao lưu

Mặc định lưu ở `~/.config/bo-go-viet/settings.json`, hoặc dưới `$XDG_CONFIG_HOME` nếu biến đó được đặt. Giao diện và engine dùng chung tệp này. Khi tệp hỏng hoặc dữ liệu sai, engine giữ cấu hình hợp lệ gần nhất; giao diện báo lỗi thay vì ghi đè âm thầm. Nếu mở ứng dụng lần đầu với tệp hỏng, dùng cấu hình mặc định để xem trước; có thể khôi phục một bản sao lưu hợp lệ.

Vào **Sao lưu & khôi phục** để xuất hoặc nhập. Khôi phục thay toàn bộ thiết lập hiện tại. Tối đa 1.000 từ viết tắt, mỗi khóa gồm 1–32 chữ cái/số ASCII, mỗi nội dung thay thế tối đa 4.096 ký tự.

## Kiểm thử

```bash
/usr/bin/python3 -m unittest discover -v
dbus-run-session -- /usr/bin/python3 integration_check.py
/usr/bin/python3 ui_check.py /tmp/bo-go-viet-preview --gtk-theme Yaru --theme light
/usr/bin/python3 ui_check.py /tmp/bo-go-viet-dark-preview --gtk-theme Yaru --theme dark
```

- **46 bài kiểm thử tự động đã qua:** Telex/VNI (240 tổ hợp nguyên âm, dấu và hoa/thường), đặt dấu, Backspace, Esc, phím tắt, trường riêng tư, gõ tắt, chuyển cấu hình, nhập dữ liệu sai, cài/gỡ vào thư mục tạm, thuộc tính gạch chân và hai chế độ nhập trực tiếp. Có kiểm tra không xóa văn bản khi con trỏ/vùng chọn thay đổi hoặc phản hồi của ứng dụng bị trễ ở chế độ kiểm tra văn bản, thứ tự xóa/chèn khi dùng phím, hàng đợi phím, hủy chèn khi mất focus và lưu chẩn đoán qua các lần đổi focus.
- **Kiểm tra IBus/D-Bus đã qua:** tạo phiên IBus riêng, gửi sự kiện phím thật, kiểm tra preedit/commit, Backspace, Esc, chuyển Việt/Anh, bỏ qua trường mật khẩu, đổi từ Telex sang VNI khi đang soạn và gõ tắt. Client kiểm thử còn xác nhận nhập trực tiếp từng phím, sửa dấu, Esc, gõ tắt, quay về soạn từ khi thay đổi vùng chọn và chế độ qua phím khi không có hỗ trợ surrounding text. Kiểm thử tự động này không đổi nguồn bàn phím của phiên người dùng.
- **Thử trong ô chat thực tế:** người dùng đã xác nhận `Phamj` → `Phạm`, không có gạch chân, bằng chế độ qua phím sau khi sửa thứ tự xóa/chèn. Việc này không chứng minh tương thích với mọi ô nhập hoặc mọi tốc độ gõ.
- **Kiểm tra 0.3.2 bằng phím thật:** hồ sơ/tệp tạm riêng trong VS Code X11 và ô nhập localhost của Chrome X11 nhận đúng `Phạm Tôi yêu tiếng Việt`; thử xóa nhanh liên tục rồi gõ ngay ký tự tiếp theo cũng cho kết quả đúng. Backspace thông thường không tạo bộ hẹn giờ trong engine; khoảng chờ khi thực sự thay chữ có dấu vẫn được giữ để bảo đảm thứ tự xử lý.
- **Kiểm tra GTK đã qua:** cả năm trang dưới Yaru sáng và tối, độ tương phản chữ điều hướng/nút đóng, chuyển theme khi cửa sổ đang mở, lưu cấu hình, tùy chọn nhập trực tiếp/gạch chân, xem trước VNI, thêm/xóa gõ tắt và chuyển văn bản. `ui_check.py` cần phiên màn hình; dùng thư mục cấu hình tạm riêng và có thể xuất ảnh giao diện.

Chưa xác nhận gõ tương tác trong Firefox, ứng dụng Electron, Terminal và mọi ứng dụng trên X11/Wayland. Khả năng tương thích phụ thuộc vào hỗ trợ IBus của ứng dụng. Trường mật khẩu, PIN và trường riêng tư được bỏ qua khi ứng dụng khai báo đúng loại trường.

## Phạm vi

Bản 0.3.2 có giao diện và các chức năng nêu trên, chưa tương đương toàn bộ XKey: chưa có Smart Switch theo ứng dụng, tự phát hiện Telex/VNI, kiểm tra chính tả, từ điển tiếng Việt, Quick Telex, dịch thuật, bảng mã TCVN3/VNI Windows hay tự cập nhật. Engine vẫn dựa trên quy tắc ghép dấu; chưa bảo đảm tất cả chuỗi phím cho kết quả giống UniKey/XKey. Bản này không dùng dữ liệu từ điển GPL của dự án tham khảo.

## Đóng gói

```bash
/usr/bin/python3 package.py
```

Tạo `dist/bo-go-viet-0.3.2.tar.gz` và tệp SHA-256. Gói chứa ứng dụng, trình cài, tài liệu và kiểm thử; không chứa thư mục macOS `xkey/` hay cấu hình cá nhân. Giải nén rồi chạy các lệnh mở/cài ở trên. Đây là gói mã nguồn chạy với Python hệ thống, không phải `.deb`.

## Gỡ bỏ

```bash
/usr/bin/python3 enable.py --remove
sudo /usr/bin/python3 install.py --uninstall
```

Đăng xuất/đăng nhập để IBus làm mới danh sách. Cấu hình cá nhân được giữ lại; bạn có thể tự xóa `~/.config/bo-go-viet` nếu không cần nữa.

## Mã nguồn

`telex.py` và `composer.py` xử lý Telex/VNI, gõ tắt và chuyển văn bản. `direct.py` kiểm tra phần văn bản vừa nhập; `settings.py` quản lý cấu hình. `engine.py` tích hợp IBus và hàng đợi phím tương thích; `runtime_status.py` lưu trạng thái không chứa nội dung. `preferences.py` là cửa sổ GTK. `install.py` và `enable.py` đăng ký bộ gõ; `package.py` đóng gói. `demo.py` vẫn dùng để thử Telex từng dòng trong Terminal.

Giấy phép MIT, xem `LICENSE`.
