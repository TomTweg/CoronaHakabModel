#include <map>
#include <vector>
#include <tuple>
#include <unordered_set>

typedef float dtype;

// todo benchmark

class MagicOperator{
    public:
        //invariant: if w_val = 0 or v_val = 0, operate(w_val, v_val) = 1
        virtual dtype operate(dtype w_val, dtype v_val) const;
};

class ManifestMatrix;

class SparseMatrix{
    private:
        // note, each column set only stores indices that might not be zero, the only guarantee
        // is that if in index is non-zero, it will appear in in the column set
        size_t* row_lens;
        size_t** row_indices;
        dtype** row_probs;
        dtype** row_values;
        dtype* prob_row_coefficients;
        dtype* prob_column_coefficients;
        dtype* value_row_offsets;
        dtype* value_column_offsets;
        size_t _nz_count;

        int col_ind(size_t row, size_t col) const;

        friend class ManifestMatrix;
    public:
        const size_t size;

        SparseMatrix(size_t size);
        void batch_set(size_t row, size_t const* A_columns, size_t c_len, dtype const* A_probs, size_t p_len, dtype const* A_values, size_t v_len);
        bool has_value(size_t row,size_t column) const;
        std::tuple<dtype, dtype> get(size_t row,size_t column) const;
        size_t nz_count();
        ManifestMatrix* manifest(dtype const* A_rolls, size_t r_len);

        void row_set_prob_coff(size_t row, dtype coff);
        void col_set_prob_coff(size_t column, dtype coff);

        void row_set_value_offset(size_t row, dtype offset);
        void col_set_value_offset(size_t column, dtype offset);

        virtual ~SparseMatrix();
};

class ManifestMatrix{
    private:
        SparseMatrix const* origin;
        bool** is_manifest;
        ManifestMatrix(SparseMatrix* const & origin);

        friend class SparseMatrix;
    public:
        dtype get(size_t row,size_t column);
        void I_POA(dtype const* A_values, size_t v_len, size_t const* A_nz_indices, size_t nzi_len,
            MagicOperator* const& op,
            dtype** AF_out, size_t* o_len);
        std::vector<std::vector<size_t>> nz_rows();
        virtual ~ManifestMatrix();
};