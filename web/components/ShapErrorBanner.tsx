export default function ShapErrorBanner({ message }: { message: string }) {
  return (
    <div className="alert alert-warning">
      The SHAP explainer could not compute feature contributions for this page ({message}). The
      sections below are empty because the explanation failed, not because this page has no
      strong drivers.
    </div>
  );
}
