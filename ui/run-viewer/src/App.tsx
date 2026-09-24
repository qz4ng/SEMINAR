import { getRun } from './data/loadRun';
import RunHeader from './components/RunHeader';
import ErrorBanner from './components/ErrorBanner';
import PipelineCanvas from './components/canvas/PipelineCanvas';
import RowFunnel from './components/RowFunnel';
import DetailDrawer from './components/drawer/DetailDrawer';
import LeftPanel from './components/panels/LeftPanel';
import CodeDictionary from './components/panels/CodeDictionary';
import ContextPage from './components/context/ContextPage';
import { useUIStore } from './store/uiStore';

const run = getRun();

function App() {
  const view = useUIStore(s => s.view);
  return (
    <div className="h-screen w-screen overflow-hidden bg-bg text-text">
      <div className="hidden lg:flex flex-col h-full w-full">
        <RunHeader run={run} />
        {view === 'run' && <ErrorBanner run={run} />}
        {/* Thân trang: drawer và từ điển mã định vị theo khối này, không theo header,
            nên header cao bao nhiêu cũng không cần chỉnh lại top-… */}
        <div className="relative flex flex-1 min-h-0 overflow-hidden">
          <LeftPanel run={run} />
          {view === 'run' ? (
            <>
              <main className="relative flex flex-1 min-w-0 flex-col">
                <PipelineCanvas run={run} />
                <RowFunnel run={run} />
              </main>
              <DetailDrawer run={run} />
            </>
          ) : (
            <ContextPage run={run} />
          )}
          <CodeDictionary />
        </div>
      </div>
      <div className="lg:hidden flex h-full w-full items-center justify-center p-6 text-center text-text-muted">
        Hãy mở trên màn hình rộng hơn (từ 1024px).
      </div>
    </div>
  );
}

export default App;
