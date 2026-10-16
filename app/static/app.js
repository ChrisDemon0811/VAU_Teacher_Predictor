const form = document.querySelector("#prediction-form");
const submitButton = document.querySelector("#submit-button");
const formError = document.querySelector("#form-error");
const statusArea = document.querySelector("#prediction-status");
const resultsSection = document.querySelector("#results-section");
const resultCards = document.querySelector("#result-cards");
const resultNotice = document.querySelector("#result-notice");
const resultTieWarning = document.querySelector("#result-tie-warning");
const resultWarning = document.querySelector("#result-warning");
const resultModel = document.querySelector("#result-model");
const startInput = document.querySelector("#tiet-bat-dau");
const endInput = document.querySelector("#tiet-ket-thuc");
const modeLabel = document.querySelector("#mode-label");

const scoreFormatter = new Intl.NumberFormat("vi-VN", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 3,
});
const percentFormatter = new Intl.NumberFormat("vi-VN", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

function setMode() {
  const hasAnyPeriod = startInput.value !== "" || endInput.value !== "";
  modeLabel.textContent = hasAnyPeriod ? "Mô hình nâng cao" : "Mô hình cơ bản";
  document.querySelector("#mode-dot").classList.toggle("advanced", hasAnyPeriod);
}

startInput.addEventListener("input", setMode);
endInput.addEventListener("input", setMode);

function showFormError(message) {
  formError.textContent = message;
  formError.hidden = false;
}

function clearMessages() {
  formError.hidden = true;
  formError.textContent = "";
  statusArea.innerHTML = "";
}

function validateForm() {
  const thu = document.querySelector("#thu").value;
  const buoi = document.querySelector("#buoi").value;
  const phong = document.querySelector("#phong").value.trim();
  if (!thu) return "Vui lòng chọn thứ trong tuần.";
  if (!buoi) return "Vui lòng chọn buổi học.";
  if (!phong) return "Vui lòng nhập phòng học.";

  const hasStart = startInput.value !== "";
  const hasEnd = endInput.value !== "";
  if (hasStart !== hasEnd) return "Nếu nhập tiết học, vui lòng nhập cả tiết bắt đầu và tiết kết thúc.";
  if (hasStart) {
    const start = Number(startInput.value);
    const end = Number(endInput.value);
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1 || end > 20) {
      return "Tiết học phải là số nguyên trong phạm vi từ 1 đến 20.";
    }
    if (start > end) return "Tiết bắt đầu phải nhỏ hơn hoặc bằng tiết kết thúc.";
  }
  return "";
}

function createDetail(label, value) {
  const item = document.createElement("li");
  const icon = document.createElement("span");
  icon.className = "detail-icon";
  icon.textContent = "✓";
  const text = document.createElement("p");
  const strong = document.createElement("strong");
  strong.textContent = `${label}: `;
  text.append(strong, document.createTextNode(value));
  item.append(icon, text);
  return item;
}

function renderResults(data) {
  resultCards.replaceChildren();
  const isColdStart = data.toa_moi_chua_co_lich_su === true;
  const isAdvanced = data.model.toLowerCase().includes("advanced");
  resultModel.textContent = isColdStart
    ? `Cold-start · ${isAdvanced ? "Nâng cao" : "Cơ bản"}`
    : isAdvanced ? "Mô hình nâng cao" : "Mô hình cơ bản";
  resultNotice.className = `result-notice ${data.du_doan_co_co_so_kiem_dinh ? "verified" : "caution"}`;
  resultNotice.textContent = isColdStart
    ? data.thong_bao
    : data.du_doan_co_co_so_kiem_dinh
    ? data.thong_bao
    : "Độ tin cậy chưa được kiểm chứng đủ. Kết quả chỉ mang tính tham khảo.";
  resultWarning.textContent = data.canh_bao;
  renderTieWarning(data);

  data.ket_qua.forEach((item, index) => {
    const explanation = item.giai_thich || {};
    const card = document.createElement("article");
    card.className = `result-card rank-${index + 1}`;

    const top = document.createElement("div");
    top.className = "rank-row";
    const rank = document.createElement("span");
    rank.className = "rank-badge";
    rank.textContent = String(index + 1);
    const rankLabel = document.createElement("span");
    rankLabel.className = "rank-label";
    rankLabel.textContent = `Xếp hạng ${index + 1}`;
    top.append(rank, rankLabel);

    const name = document.createElement("h3");
    name.textContent = item.giang_vien;

    const score = document.createElement("div");
    score.className = "score-block";
    score.innerHTML = `<span>Điểm xếp hạng</span><strong>${scoreFormatter.format(item.diem_xep_hang)}</strong><small>Không phải xác suất %</small>`;

    const history = document.createElement("div");
    history.className = "history-count";
    history.innerHTML = `<strong>${item.so_ca_lich_su_trung_thu_buoi ?? explanation.so_ca_cung_thu_buoi ?? 0}</strong><span>ca lịch sử trùng thứ và buổi</span>`;

    const details = document.createElement("ul");
    details.className = "evidence-list";
    if (explanation.la_toa_moi) {
      const signals = explanation.co_su_dung_tiet_de_xep_hang
        ? "thứ, buổi và khoảng tiết; không dùng tòa, tầng hoặc phòng"
        : "thứ và buổi; không dùng tòa, tầng hoặc phòng";
      details.append(createDetail("Cơ sở cold-start", signals));
    }
    if (explanation.phong_da_day_cung_thu_buoi?.length) {
      details.append(createDetail("Phòng từng dạy cùng khung", explanation.phong_da_day_cung_thu_buoi.join(", ")));
    }
    if (explanation.la_phong_online) {
      details.append(createDetail("Phòng Online", "không áp dụng tòa hoặc tầng vật lý"));
    } else {
      if (explanation.so_ca_cung_toa_nha > 0) {
        details.append(createDetail("Cùng tòa nhà", `${explanation.so_ca_cung_toa_nha} ca đã ghi nhận`));
      }
      if (explanation.so_ca_cung_tang > 0) {
        details.append(createDetail("Cùng tầng", `${explanation.so_ca_cung_tang} ca đã ghi nhận`));
      }
    }
    if (explanation.hoc_ky_co_du_lieu?.length) {
      details.append(createDetail("Học kỳ có dữ liệu", explanation.hoc_ky_co_du_lieu.join(", ")));
    }

    card.append(top, name, score, history, details);
    resultCards.append(card);
  });

  resultsSection.hidden = false;
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderTieWarning(data) {
  resultTieWarning.replaceChildren();
  const count = Number(data.so_giang_vien_dong_diem_cao_nhat || 0);
  const teachers = Array.isArray(data.giang_vien_dong_diem_cao_nhat)
    ? data.giang_vien_dong_diem_cao_nhat
    : [];
  if (count <= 3 || teachers.length === 0) {
    resultTieWarning.hidden = true;
    return;
  }

  const heading = document.createElement("strong");
  heading.textContent = `${count} giảng viên đồng điểm cao nhất`;
  const explanation = document.createElement("p");
  explanation.textContent = "Top 3 chỉ là ba người đứng đầu theo quy tắc xếp phụ. Danh sách đầy đủ:";
  const list = document.createElement("ol");
  teachers.forEach((teacher) => {
    const item = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = teacher.giang_vien;
    const details = document.createElement("small");
    details.textContent = `Điểm ${scoreFormatter.format(teacher.diem_xep_hang)} · ${teacher.so_ca_lich_su_trung_thu_buoi} ca trùng thời gian`;
    item.append(name, details);
    list.append(item);
  });
  resultTieWarning.append(heading, explanation, list);
  resultTieWarning.hidden = false;
}

function setLoading(loading) {
  submitButton.disabled = loading;
  submitButton.classList.toggle("loading", loading);
  submitButton.querySelector(".button-label").textContent = loading ? "Đang phân tích dữ liệu…" : "Dự đoán giảng viên";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessages();
  const error = validateForm();
  if (error) {
    showFormError(error);
    return;
  }

  const payload = {
    thu: Number(document.querySelector("#thu").value),
    buoi: document.querySelector("#buoi").value,
    phong: document.querySelector("#phong").value.trim(),
    tiet_bat_dau: startInput.value === "" ? null : Number(startInput.value),
    tiet_ket_thuc: endInput.value === "" ? null : Number(endInput.value),
  };

  setLoading(true);
  statusArea.innerHTML = '<div class="loading-status"><span class="spinner visible"></span> Đang so khớp với dữ liệu lịch sử…</div>';
  resultsSection.hidden = true;

  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Dữ liệu không hợp lệ.");
    if (!data.ket_qua?.length) {
      statusArea.innerHTML = '<div class="empty-status">Không tìm thấy kết quả phù hợp trong dữ liệu lịch sử.</div>';
      return;
    }
    statusArea.innerHTML = "";
    renderResults(data);
  } catch (requestError) {
    const message = requestError instanceof TypeError
      ? "Không thể kết nối đến máy chủ. Vui lòng kiểm tra server và thử lại."
      : requestError.message;
    statusArea.innerHTML = "";
    showFormError(message);
  } finally {
    setLoading(false);
  }
});

function metricCard(title, type, metrics) {
  const article = document.createElement("article");
  article.className = "metric-card";
  const heading = document.createElement("div");
  heading.className = "metric-heading";
  const label = document.createElement("span");
  label.textContent = type;
  const name = document.createElement("h3");
  name.textContent = title;
  heading.append(label, name);
  const grid = document.createElement("div");
  grid.className = "metric-grid";
  [
    ["Top 1", metrics.validation.top1, metrics.test_reference.top1],
    ["Top 3", metrics.validation.top3, metrics.test_reference.top3],
    ["Độ phủ GV", metrics.validation.teacher_coverage, metrics.test_reference.teacher_coverage],
  ].forEach(([metricName, validation, test]) => {
    const row = document.createElement("div");
    row.innerHTML = `<strong>${metricName}</strong><span>Validation <b>${percentFormatter.format(validation)}</b></span><span>Test tham khảo <b>${percentFormatter.format(test)}</b></span>`;
    grid.append(row);
  });
  const count = document.createElement("p");
  count.className = "metric-count";
  count.textContent = `${metrics.validation.rows} mẫu Validation · ${metrics.test_reference.rows} mẫu Test tham khảo`;
  article.append(heading, grid, count);
  return article;
}

async function loadMetadata() {
  try {
    const response = await fetch("/api/metadata");
    if (!response.ok) throw new Error();
    const data = await response.json();
    const roomOptions = document.querySelector("#room-options");
    const rooms = [...new Set([
      ...data.phong_goi_y,
      ...(data.phong_cold_start_goi_y || []),
    ])];
    rooms.forEach((room) => {
      const option = document.createElement("option");
      option.value = room;
      roomOptions.append(option);
    });

    const cards = document.querySelector("#metric-cards");
    cards.replaceChildren(
      metricCard("Không sử dụng khoảng tiết", "Mô hình cơ bản", data.models.basic),
      metricCard("Có sử dụng khoảng tiết", "Mô hình nâng cao", data.models.advanced),
    );
  } catch {
    document.querySelector("#metric-cards").innerHTML = '<p class="metadata-error">Chưa thể tải số liệu đánh giá mô hình.</p>';
  }
}

loadMetadata();
setMode();
