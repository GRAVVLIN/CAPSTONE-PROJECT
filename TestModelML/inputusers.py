import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

class PersonalFinanceApp:
    def __init__(self):
        # Inisialisasi session state
        if 'pendapatan' not in st.session_state:
            st.session_state.pendapatan = {}
        if 'pengeluaran' not in st.session_state:
            st.session_state.pengeluaran = {}
        
        # Konfigurasi halaman
        st.set_page_config(page_title="Aplikasi Keuangan Pribadi", layout="wide")

    def hitung_penghematan(self, total_pendapatan, persentase_penghematan):
        """Menghitung target penghematan berdasarkan total pendapatan."""
        return total_pendapatan * persentase_penghematan

    def deteksi_anomali(self, pengeluaran_bulanan, rata_rata_pengeluaran, threshold=2):
        """Mendeteksi pengeluaran yang melebihi threshold rata-rata."""
        return [x for x in pengeluaran_bulanan if x > threshold * rata_rata_pengeluaran]

    def input_pendapatan(self):
        """Input pendapatan melalui dropdown kategori."""
        st.subheader("🔼 Masukkan Pendapatan")
        kategori_pendapatan = st.selectbox("Kategori Pendapatan", ["Gaji", "Bonus", "Investasi"], key="kategori_pendapatan")
        jumlah_pendapatan = st.number_input("Jumlah Pendapatan (Rp)", min_value=0.0, step=1000.0, key="jumlah_pendapatan")
        
        if st.button("Tambah Pendapatan", key="btn_tambah_pendapatan"):
            if kategori_pendapatan and jumlah_pendapatan > 0:
                st.session_state.pendapatan[kategori_pendapatan] = st.session_state.pendapatan.get(kategori_pendapatan, 0) + jumlah_pendapatan
                st.success(f"Pendapatan kategori '{kategori_pendapatan}' sebesar Rp {jumlah_pendapatan:,.0f} ditambahkan.")
            else:
                st.warning("Masukkan jumlah pendapatan dengan benar.")

    def input_pengeluaran(self):
        """Input pengeluaran melalui dropdown kategori."""
        st.subheader("🔽 Masukkan Pengeluaran")
        kategori_pengeluaran = st.selectbox("Kategori Pengeluaran", ["Kebutuhan", "Hiburan", "Tabungan"], key="kategori_pengeluaran")
        jumlah_pengeluaran = st.number_input("Jumlah Pengeluaran (Rp)", min_value=0.0, step=1000.0, key="jumlah_pengeluaran")
        
        if st.button("Tambah Pengeluaran", key="btn_tambah_pengeluaran"):
            if kategori_pengeluaran and jumlah_pengeluaran > 0:
                st.session_state.pengeluaran[kategori_pengeluaran] = st.session_state.pengeluaran.get(kategori_pengeluaran, 0) + jumlah_pengeluaran
                st.success(f"Pengeluaran kategori '{kategori_pengeluaran}' sebesar Rp {jumlah_pengeluaran:,.0f} ditambahkan.")
            else:
                st.warning("Masukkan jumlah pengeluaran dengan benar.")

    def pilih_target_tabungan(self):
        """Pilih target tabungan."""
        st.subheader("💰 Target Tabungan")
        pilihan = st.radio("Pilih target tabungan:", ("Easy (30%)", "Normal (50%)", "Hard (80%)"), key="target_tabungan_radio")
        return {"Easy (30%)": 0.3, "Normal (50%)": 0.5, "Hard (80%)": 0.8}[pilihan]

    def visualisasi_keuangan(self, pendapatan, pengeluaran, target_tabungan):
        """Visualisasi grafik keuangan."""
        total_pendapatan = sum(pendapatan.values())
        total_pengeluaran = sum(pengeluaran.values())
        penghematan = self.hitung_penghematan(total_pendapatan, target_tabungan)

        st.subheader("📊 Visualisasi Keuangan")
        col1, col2 = st.columns(2)
        
        with col1:
            fig, ax = plt.subplots()
            ax.pie(pengeluaran.values(), labels=pengeluaran.keys(), autopct='%1.1f%%', startangle=90)
            ax.set_title("Pengeluaran per Kategori")
            st.pyplot(fig)

        with col2:
            fig, ax = plt.subplots()
            ax.pie([total_pendapatan, total_pengeluaran, penghematan], labels=['Pendapatan', 'Pengeluaran', 'Tabungan'], 
                   colors=['green', 'red', 'blue'], autopct='%1.1f%%', startangle=90)
            ax.set_title("Distribusi Keuangan")
            st.pyplot(fig)

    def analisis_keuangan(self, target_tabungan):
        """Analisis keuangan dengan perhitungan dan rekomendasi."""
        total_pendapatan = sum(st.session_state.pendapatan.values())
        total_pengeluaran = sum(st.session_state.pengeluaran.values())
        penghematan = self.hitung_penghematan(total_pendapatan, target_tabungan)
        pengeluaran_bulanan = list(st.session_state.pengeluaran.values())
        rata_rata_pengeluaran = np.mean(pengeluaran_bulanan) if pengeluaran_bulanan else 0
        anomali_pengeluaran = self.deteksi_anomali(pengeluaran_bulanan, rata_rata_pengeluaran)

        st.subheader("📝 Analisis Keuangan")
        saldo_sisa = total_pendapatan - total_pengeluaran - penghematan

        st.metric("Pendapatan Total", f"Rp {total_pendapatan:,.0f}")
        st.metric("Pengeluaran Total", f"Rp {total_pengeluaran:,.0f}")
        st.metric("Target Tabungan", f"Rp {penghematan:,.0f}")
        st.metric("Saldo Tersisa", f"Rp {saldo_sisa:,.0f}")

        if total_pengeluaran > total_pendapatan - penghematan:
            st.warning("Pengeluaran Anda melebihi target tabungan!")
        elif anomali_pengeluaran:
            st.warning(f"Terdeteksi anomali: {anomali_pengeluaran}")
        else:
            st.success("Keuangan Anda sehat.")

    def run(self):
        """Jalankan aplikasi."""
        st.title("💼 Aplikasi Keuangan Pribadi")

        menu = st.sidebar.radio("Menu", ["Input Pendapatan", "Input Pengeluaran", "Analisis Keuangan"])
        if menu == "Input Pendapatan":
            self.input_pendapatan()
        elif menu == "Input Pengeluaran":
            self.input_pengeluaran()
        elif menu == "Analisis Keuangan":
            if st.session_state.pendapatan and st.session_state.pengeluaran:
                target_tabungan = self.pilih_target_tabungan()
                self.visualisasi_keuangan(st.session_state.pendapatan, st.session_state.pengeluaran, target_tabungan)
                self.analisis_keuangan(target_tabungan)
            else:
                st.warning("Tambahkan pendapatan dan pengeluaran terlebih dahulu.")

if __name__ == "__main__":
    app = PersonalFinanceApp()
    app.run()