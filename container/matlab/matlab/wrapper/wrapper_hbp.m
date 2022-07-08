function wrapper_hbp(file)

myVars = {'K','Ct','offset'};
data = load(file,myVars{:});
offset = data.offset;
K_orig = data.K; % original cost matrix

Ct = data.Ct;
[n1,n2] = size(Ct);
K = - data.K;


bpoptions.outIter = 1;
bpoptions.innerIter = 5;
BaBoptions.MaxIter = 600;
BaBoptions.bpoptions = bpoptions;

tstart = tic;
fprintf('Start optimization: \n')
fprintf('Model: n1: %g n2: %g \n', n1, n2)
assign = QAP_HungarianBP(K, Ct, [], BaBoptions)

X = assign.X
lower_bound = assign.dual_bound;


curr_score = X(:)' * K_orig * X(:);
fprintf('time: %f ',toc(tstart))
fprintf('upper_bound: %f ', full(curr_score)+cast(offset,'like',full(curr_score)))
fprintf('lower_bound: %f ', -lower_bound)
indices = 1:n2;
matching = reshape(X,size(Ct))*indices';
fprintf('labeling: [')
fprintf('%g,',matching(1:end-1))
fprintf('%g] \n',matching(end))
